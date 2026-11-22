"""Run in isolated fixed-image CPU container; arguments: original patched."""
import ast
import sys
import torch

def load(path):
    tree = ast.parse(open(path).read())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('build_dspark_swa_indices', '_aligned_dspark_index_width')]
    assert len(nodes) == 2
    ns = {'torch': torch}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), ns)
    return ns['build_dspark_swa_indices']

def args():
    return dict(block_table=torch.tensor([[10,11]]), num_speculative_tokens=2, window_size=4, block_size=4, query_start_loc=torch.tensor([0,2]), seq_lens=torch.tensor([6]), num_decode_tokens=2, index_width=8)

def raises(kind, fn, **kw):
    try:
        fn(**kw)
    except Exception as exc:
        assert type(exc) is kind, (type(exc), str(exc))
        print(kind.__name__, str(exc))
    else:
        raise AssertionError('expected '+kind.__name__)

original, patched = map(load, sys.argv[1:])
raises(NameError, original, **args())
oracle = torch.tensor([[[40,41,42,43,44,45,-1,-1]]]*2, dtype=torch.int32)
for mode in ('plain','output','buffer','both'):
    kw = args()
    output = torch.empty((2,1,8), dtype=torch.int32)
    buffer = torch.full((3,1,8), -777, dtype=torch.int32)
    if mode in ('output','both'): kw['indices_output'] = output
    if mode in ('buffer','both'): kw['buffer'] = buffer
    result, lens = patched(**kw)
    assert result.shape == (2,1,8) and torch.equal(result, oracle)
    assert torch.equal(lens, torch.tensor([6,6]))
    if mode in ('output','both'): assert torch.equal(output, oracle)
    if mode == 'output': assert result is output
    if mode in ('buffer','both'):
        assert result.data_ptr() == buffer.data_ptr()
        assert torch.all(buffer[2] == -777)
    print(mode, 'oracle/shape/alias PASS')
kw=args(); kw['block_table']=torch.tensor([[10,11],[12,13]])
raises(NameError, original, **kw)
raises(RuntimeError, patched, **kw)
kw=args(); kw['indices_output']=torch.empty((1,1,8),dtype=torch.int32)
raises(ValueError, patched, **kw)
kw=args(); kw['buffer']=torch.empty((1,1,8),dtype=torch.int32)
raises(AssertionError, patched, **kw)
print('PASS all CPU regression cases; torch', torch.__version__)
