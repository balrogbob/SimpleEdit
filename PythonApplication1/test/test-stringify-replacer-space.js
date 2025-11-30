// test-stringify-replacer-space.js
var obj = {
  a: 1,
  b: 2,
  c: function(){},
  d: undefined,
  toJSON: function(k) { return {a: this.a + 10, extra: "ok"}; }
};
// replacer function example
function rep(key, value) {
  if (key === 'extra') return undefined;
  return (typeof this[key] !== 'undefined') ? this[key] : value;
}
console.log("toJSON result:", obj.toJSON(""));
console.log("compact:", JSON.stringify(obj));
console.log("pretty 2:", JSON.stringify(obj, null, 2));
console.log("with replacer fn:", JSON.stringify(obj, rep, 2));
// replacer array example
console.log("replacer array:", JSON.stringify({x:1,y:2,z:3}, ['y','x'], 2));
console.log("replacer call example:", rep.call({x:1}, "x", 1));