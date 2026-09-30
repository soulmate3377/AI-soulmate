from modelscope import snapshot_download


model_dir = snapshot_download(
    'AI-ModelScope/bge-small-zh-v1.5'
)


print(model_dir)