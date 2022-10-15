import os
from pathlib import Path
import numpy as np
from tqdm import tqdm
from PIL import Image

LEIPZIG_PATH = Path('/home/macosta/ttmp/primus-leipzig/')
LEIPZIG_TXT_PATH = Path('/home/macosta/ttmp/primus-leipzig-txt/')
LEIPZIG_TXT_PATH.mkdir(exist_ok=True)
for path in tqdm(os.listdir(LEIPZIG_PATH)):
    savepath = LEIPZIG_TXT_PATH / f"{Path(path).name.split('.')[0]}.txt"
    if os.path.isfile(savepath):
        continue
    img = Image.open(LEIPZIG_PATH / path)
    arr = np.array(img, dtype=np.uint8)
    arr = 1 - arr
    arr_T = arr.T
    words = [''.join(str(x) for x in row) for row in arr_T]
    words = ' '.join(words)
    with open(savepath, 'w') as f:
        f.write(words)
