"""
RWKV "x051a" model - does not require custom CUDA kernel to train :)

References:
https://github.com/BlinkDL/RWKV-LM

Inference:
Always fast, and VRAM will not grow, because RWKV does not need KV cache.

Training:
Because we are not using custom CUDA kernel here, training is slightly slower than gpt+flash_attn when ctxlen is short.
Training becomes faster than gpt+flash_attn when ctxlen is long.
"""

import math, warnings
import inspect
from dataclasses import dataclass
from functools import lru_cache  # added for cached w matrix builder

import torch
import torch.nn as nn
from torch.nn import functional as F

class LayerNorm(nn.Module):
    """ LayerNorm but with an optional bias. PyTorch doesn't support simply bias=False """

    def __init__(self, ndim, bias):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(ndim))
        self.bias = nn.Parameter(torch.zeros(ndim)) if bias else None

    def forward(self, input):
        return F.layer_norm(input, self.weight.shape, self.weight, self.bias, 1e-5)

class RWKV_TimeMix_x051a(nn.Module):
    def __init__(self, config, layer_id):
        super().__init__()
        assert config.n_embd % config.n_head == 0
        self.head_size = config.n_embd // config.n_head
        self.n_head = config.n_head

        with torch.no_grad():
            ratio_0_to_1 = layer_id / (config.n_layer - 1)  # 0 to 1
            ratio_1_to_almost0 = 1.0 - (layer_id / config.n_layer)  # 1 to ~0
            ddd = torch.arange(config.n_embd, dtype=torch.float32).view(1, 1, -1) / config.n_embd

            self.time_maa_k = nn.Parameter(1.0 - torch.pow(ddd, ratio_1_to_almost0))
            self.time_maa_v = nn.Parameter(1.0 - (torch.pow(ddd, ratio_1_to_almost0) + 0.3 * ratio_0_to_1))
            self.time_maa_r = nn.Parameter(1.0 - torch.pow(ddd, 0.5 * ratio_1_to_almost0))
            self.time_maa_g = nn.Parameter(1.0 - torch.pow(ddd, 0.5 * ratio_1_to_almost0))

            decay_speed = torch.linspace(0, 1, self.n_head)
            decay_speed = -6 + 5 * torch.pow(decay_speed, (0.7 + 1.3 * ratio_0_to_1))
            self.time_decay = nn.Parameter(decay_speed.unsqueeze(-1))

            tmp = ratio_0_to_1 * (1 - torch.linspace(0, 1, self.n_head))
            self.time_faaaa = nn.Parameter(tmp.unsqueeze(-1))

        self.time_shift = nn.ZeroPad2d((0, 0, 1, -1))
        self.receptance = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.key = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.value = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.gate = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.output = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.ln_x = nn.GroupNorm(self.n_head, config.n_embd, eps=(1e-5)*64)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        B, T, C = x.size()
        H, N = self.n_head, self.head_size

        if T % 256 == 0:
            Q = 256
        elif T % 128 == 0:
            Q = 128
        else:
            Q = T
            if not self.training:
                warnings.warn(
                    '\n' + '#' * 80 + '\n\n'
                    'Note: Using training-mode TimeMix path for inference with sequence length '
                    f'{T}. Consider implementing a streaming/incremental inference path for RWKV.\n\n'
                    + '#' * 80 + '\n'
                )
        assert T % Q == 0

        xx = self.time_shift(x) - x
        xk = x + xx * self.time_maa_k
        xv = x + xx * self.time_maa_v
        xr = x + xx * self.time_maa_r
        xg = x + xx * self.time_maa_g

        r = self.receptance(xr).view(B, T, H, N).transpose(1, 2)               # (B,H,T,N)
        k = self.key(xk).view(B, T, H, N).transpose(1, 2).transpose(2, 3)       # (B,H,N,T)
        v = self.value(xv).view(B, T, H, N).transpose(1, 2)                     # (B,H,T,N)
        g = F.silu(self.gate(xg))                                               # (B,T,C)

        w_decay = torch.exp(-torch.exp(self.time_decay.float()))                # (H,1)
        u_first = self.time_faaaa.float()                                       # (H,1)

        @lru_cache(maxsize=8)
        def build_w_mats(cache_Q, dtype_str, device_str):
            device = torch.device(device_str)
            dtype = getattr(torch, dtype_str)
            ind = torch.arange(cache_Q - 1, -1, -1, device=device).unsqueeze(0).repeat(H, 1)
            w_local = w_decay.to(device).repeat(1, cache_Q).pow(ind)            # (H,Q)
            wk_local = w_local.view(H, 1, cache_Q)                              # (H,1,Q)
            wb_local = wk_local.transpose(-2, -1).flip(1)                       # (H,Q,1)
            w2 = torch.cat([w_local[:, 1:], u_first.to(device)], dim=1)
            w2 = F.pad(w2, (0, cache_Q))
            w2 = torch.tile(w2, [cache_Q])[:, :-cache_Q].view(H, cache_Q, 2 * cache_Q - 1)
            w2 = w2[:, :, cache_Q - 1:].view(H, cache_Q, cache_Q)               # (H,Q,Q)
            ws_local = w_decay.pow(cache_Q).to(device).view(H, 1, 1)            # (H,1,1)
            return (w2.to(dtype), wk_local.to(dtype), wb_local.to(dtype), ws_local.to(dtype))

        w, wk, wb, ws = build_w_mats(Q, r.dtype.__str__().split('.')[-1], r.device.type)

        state = torch.zeros(B, H, N, N, device=r.device, dtype=r.dtype)
        y = torch.empty(B, H, T, N, device=r.device, dtype=r.dtype)

        for i in range(T // Q):
            rr = r[:, :, i * Q:(i + 1) * Q, :]          # (B,H,Q,N)
            kk = k[:, :, :, i * Q:(i + 1) * Q]          # (B,H,N,Q)
            vv = v[:, :, i * Q:(i + 1) * Q, :]          # (B,H,Q,N)
            att_part = ((rr @ kk) * w.unsqueeze(0)) @ vv
            mem_part = (rr @ state) * wb.unsqueeze(0)
            y[:, :, i * Q:(i + 1) * Q, :] = att_part + mem_part
            state = ws.unsqueeze(0) * state + (kk * wk.unsqueeze(0)) @ vv

        y = y.transpose(1, 2).contiguous().view(B * T, C)
        y = self.ln_x(y).view(B, T, C) * g
        y = self.dropout(self.output(y))
        return y

class RWKV_ChannelMix_x051a(nn.Module):
    def __init__(self, config, layer_id):
        super().__init__()
        self.time_shift = nn.ZeroPad2d((0, 0, 1, -1))
        with torch.no_grad():
            ratio_1_to_almost0 = 1.0 - (layer_id / config.n_layer)
            ddd = torch.ones(1, 1, config.n_embd)
            for i in range(config.n_embd):
                ddd[0, 0, i] = i / config.n_embd
            self.time_maa_k = nn.Parameter(1.0 - torch.pow(ddd, ratio_1_to_almost0))
            self.time_maa_r = nn.Parameter(1.0 - torch.pow(ddd, ratio_1_to_almost0))
        self.key = nn.Linear(config.n_embd, 3 * config.n_embd, bias=config.bias)
        self.value = nn.Linear(3 * config.n_embd, config.n_embd, bias=config.bias)
        self.receptance = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        xx = self.time_shift(x) - x
        xk = x + xx * self.time_maa_k
        xr = x + xx * self.time_maa_r
        x = self.key(xk)
        x = torch.relu(x) ** 2
        x = self.value(x)
        x = torch.sigmoid(self.receptance(xr)) * x
        x = self.dropout(x)
        return x

class Block(nn.Module):
    def __init__(self, config, layer_id):
        super().__init__()
        self.ln_1 = LayerNorm(config.n_embd, bias=config.bias)
        self.tmix = RWKV_TimeMix_x051a(config, layer_id)
        self.ln_2 = LayerNorm(config.n_embd, bias=config.bias)
        self.cmix = RWKV_ChannelMix_x051a(config, layer_id)  # restored original channel mix

    def forward(self, x):
        x = x + self.tmix(self.ln_1(x))
        x = x + self.cmix(self.ln_2(x))
        return x

@dataclass
class GPTConfig:
    block_size: int = 1024
    vocab_size: int = 50304
    n_layer: int = 12
    n_head: int = 12
    n_embd: int = 768
    dropout: float = 0.0
    bias: bool = True
    gradient_checkpointing: bool = False

class GPT(nn.Module):
    def __init__(self, config):
        super().__init__()
        assert config.vocab_size is not None
        assert config.block_size is not None
        self.config = config
        self.transformer = nn.ModuleDict(dict(
            wte=nn.Embedding(config.vocab_size, config.n_embd),
            wpe=nn.Embedding(config.block_size, config.n_embd),
            drop=nn.Dropout(config.dropout),
            h=nn.ModuleList([Block(config, i) for i in range(config.n_layer)]),
            ln_f=LayerNorm(config.n_embd, bias=config.bias),
        ))
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        self.lm_head.weight = self.transformer.wte.weight  # weight tying

        self.apply(self._init_weights)
        for pn, p in self.named_parameters():
            if pn.endswith('tmix.output.weight'):
                torch.nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * config.n_layer))

        print(f"number of parameters: {self.get_num_params()/1e6:.2f}M")

    def enable_gradient_checkpointing(self):
        self.config.gradient_checkpointing = True

    def get_num_params(self, non_embedding=True):
        n_params = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n_params -= self.transformer.wpe.weight.numel()
        return n_params

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx, targets=None):
        device = idx.device
        b, t = idx.size()
        assert t <= self.config.block_size, f"Cannot forward sequence of length {t}, block size is only {self.config.block_size}"
        pos = torch.arange(0, t, dtype=torch.long, device=device)
        tok_emb = self.transformer.wte(idx)
        pos_emb = self.transformer.wpe(pos)
        x = self.transformer.drop(tok_emb + pos_emb)

        if self.config.gradient_checkpointing and self.training:
            def run_block(block, hidden):
                return block(hidden)
            for block in self.transformer.h:
                x = torch.utils.checkpoint.checkpoint(run_block, block, x, use_reentrant=False)
        else:
            for block in self.transformer.h:
                x = block(x)

        x = self.transformer.ln_f(x)

        if targets is not None:
            logits = self.lm_head(x)
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-1)
        else:
            logits = self.lm_head(x[:, [-1], :])
            loss = None
        return logits, loss

    def crop_block_size(self, block_size):
        assert block_size <= self.config.block_size
        self.config.block_size = block_size
        self.transformer.wpe.weight = nn.Parameter(self.transformer.wpe.weight[:block_size])

    @classmethod
    def from_pretrained(cls, model_type, override_args=None):
        assert model_type in {'gpt2', 'gpt2-medium', 'gpt2-large', 'gpt2-xl'}
        override_args = override_args or {}
        assert all(k == 'dropout' for k in override_args)
        from transformers import GPT2LMHeadModel
        print(f"loading weights from pretrained gpt: {model_type}")

        config_args = {
            'gpt2': dict(n_layer=12, n_head=12, n_embd=768),
            'gpt2-medium': dict(n_layer=24, n_head=16, n_embd=1024),
            'gpt2-large': dict(n_layer=36, n_head=20, n_embd=1280),
            'gpt2-xl': dict(n_layer=48, n_head=25, n_embd=1600),
        }[model_type]
        print("forcing vocab_size=50257, block_size=1024, bias=True")
        config_args['vocab_size'] = 50257
        config_args['block_size'] = 1024
        config_args['bias'] = True
        if 'dropout' in override_args:
            print(f"overriding dropout rate to {override_args['dropout']}")
            config_args['dropout'] = override_args['dropout']
        config = GPTConfig(**config_args)
        model = GPT(config)
        sd = model.state_dict()
        sd_keys = list(sd.keys())

        model_hf = GPT2LMHeadModel.from_pretrained(model_type)
        sd_hf = model_hf.state_dict()
        sd_keys_hf = [k for k in sd_hf.keys()
                      if not k.endswith('.attn.masked_bias')
                      and not k.endswith('.attn.bias')]
        transposed = [
            'attn.c_attn.weight', 'attn.c_proj.weight',
            'mlp.c_fc.weight', 'mlp.c_proj.weight'
        ]
        assert len(sd_keys_hf) == len(sd_keys), f"mismatched keys: {len(sd_keys_hf)} != {len(sd_keys)}"
        for k in sd_keys_hf:
            if any(k.endswith(w) for w in transposed):
                assert sd_hf[k].shape[::-1] == sd[k].shape
                with torch.no_grad():
                    sd[k].copy_(sd_hf[k].t())
            else:
                assert sd_hf[k].shape == sd[k].shape
                with torch.no_grad():
                    sd[k].copy_(sd_hf[k])
        return model

    def configure_optimizers(self, weight_decay, learning_rate, betas, device_type):
        param_dict = {pn: p for pn, p in self.named_parameters() if p.requires_grad}
        decay_params = [p for n, p in param_dict.items() if p.dim() >= 2 and 'time_' not in n]
        nodecay_params = [p for n, p in param_dict.items() if p.dim() < 2 or 'time_' in n]
        optim_groups = [
            {'params': decay_params, 'weight_decay': weight_decay},
            {'params': nodecay_params, 'weight_decay': 0.0}
        ]
        num_decay_params = sum(p.numel() for p in decay_params)
        num_nodecay_params = sum(p.numel() for p in nodecay_params)
        print(f"num decayed parameter tensors: {len(decay_params)}, with {num_decay_params:,} parameters")
        print(f"num non-decayed parameter tensors: {len(nodecay_params)}, with {num_nodecay_params:,} parameters")
        fused_available = 'fused' in inspect.signature(torch.optim.AdamW).parameters
        use_fused = fused_available and device_type == 'cuda'
        extra_args = dict(fused=True) if use_fused else {}
        optimizer = torch.optim.AdamW(optim_groups, lr=learning_rate, betas=betas, **extra_args)
        print(f"using fused AdamW: {use_fused}")
        return optimizer

    def estimate_mfu(self, fwdbwd_per_iter, dt):
        N = self.get_num_params()
        cfg = self.config
        L, H, Q, T = cfg.n_layer, cfg.n_head, cfg.n_embd // cfg.n_head, cfg.block_size
        flops_per_token = 6 * N + 12 * L * H * Q * T
        flops_per_fwdbwd = flops_per_token * T
        flops_per_iter = flops_per_fwdbwd * fwdbwd_per_iter
        flops_achieved = flops_per_iter * (1.0 / dt)
        flops_promised = 312e12
        return flops_achieved / flops_promised

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=1.0, top_k=None):
        temperature = max(1e-3, float(temperature))
        for _ in range(max_new_tokens):
            idx_cond = idx if idx.size(1) <= self.config.block_size else idx[:, -self.config.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float('Inf')
            probs = F.softmax(logits, dim=-1)
            idx_next = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, idx_next), dim=1)
        return idx