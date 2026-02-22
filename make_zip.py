import zipfile, os

files = ['solution.py', 'model.pkl', 'requirements.txt']
out = 'team-3amiiii.zip'

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f)
        print(f'Added {f}: {os.path.getsize(f)/1024/1024:.2f} MB')

total = os.path.getsize(out)/1024/1024
print(f'ZIP total: {total:.2f} MB')
