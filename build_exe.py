import PyInstaller.__main__
import os
import shutil

def build():
    print("🛠 Building Garage Hollywood Executable...")
    
    # Clean old build files
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists("dist"): shutil.rmtree("dist")
    
    params = [
        'run_studio.py',
        '--name=GarageHollywood',
        '--onedir',
        '--console',
        '--noconfirm',
        '--add-data=src;src',
        '--add-data=scripts;scripts',
        '--add-data=data;data',
        '--add-data=outputs;outputs',
        '--add-data=.env;.',
        '--hidden-import=src.local_server.main',
        '--hidden-import=pyngrok',
        '--collect-all=moviepy',
        '--collect-all=uvicorn',
        '--collect-all=psutil',
    ]
    
    # Check if webapp dist exists
    if os.path.exists("src/webapp/dist"):
        params.append('--add-data=src/webapp/dist;src/webapp/dist')

    PyInstaller.__main__.run(params)
    
    print("\n✅ Build complete! Executable is in the 'dist/GarageHollywood' folder.")
    print("👉 To run the studio, just open 'dist/GarageHollywood/GarageHollywood.exe'")

if __name__ == "__main__":
    build()
