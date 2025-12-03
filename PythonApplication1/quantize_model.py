import torch
import os
from model import GPT, GPTConfig

out_dir = 'out'
ckpt_path = os.path.join(out_dir, 'ckpt.pt')
quantized_ckpt_path = os.path.join(out_dir, 'rwkv_quantized.pth')

def should_quantize_module(name: str, module: torch.nn.Module) -> bool:
    # Quantize only internal Linear layers; skip embeddings, LayerNorms and final head
    if isinstance(module, torch.nn.LayerNorm):
        return False
    if isinstance(module, torch.nn.Embedding):
        return False
    if isinstance(module, torch.nn.Linear):
        # Exclude common output head names and embedding projections
        bad_names = ('lm_head', 'head', 'to_logits', 'proj_out')
        if any(n in name.lower() for n in bad_names):
            return False
        # Exclude obvious embedding projections if they exist
        if 'embed' in name.lower():
            return False
        return True
    return False

def quantize_model_selective(model: torch.nn.Module, dtype=torch.qint8):
    # Walk the model and wrap only selected Linear layers with dynamic quantization
    # torch.quantization.quantize_dynamic accepts a module class set; we’ll apply it selectively.
    for name, module in model.named_modules():
        if should_quantize_module(name, module):
            # Replace in-place with a quantized Linear
            parent = model
            parts = name.split('.')
            for p in parts[:-1]:
                parent = getattr(parent, p)
            last = parts[-1]
            qmod = torch.quantization.quantize_dynamic(
                module, {torch.nn.Linear}, dtype=dtype
            )
            setattr(parent, last, qmod)
    return model

if __name__ == "__main__":
    # Load float checkpoint
    checkpoint = torch.load(ckpt_path, map_location='cpu')
    config = GPTConfig(**checkpoint['model_args'])
    model = GPT(config)
    model.load_state_dict(checkpoint['model'])
    model.eval()

    # Selective quantization (Linear-only, skip embeddings/LayerNorm/output head)
    qmodel = quantize_model_selective(model, dtype=torch.qint8)

    # Save dict-format with flag
    torch.save({
        'model_args': checkpoint['model_args'],
        'model': qmodel.state_dict(),
        'quantized': True
    }, quantized_ckpt_path)
    print(f"Model quantized and saved as {quantized_ckpt_path}")
