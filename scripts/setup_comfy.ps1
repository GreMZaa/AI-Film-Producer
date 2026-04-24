# Setup ComfyUI for Garage Hollywood
# This script will install necessary custom nodes for Flux GGUF

param (
    [string]$ComfyPath = "D:\ComfyUI"
)

Write-Host "--- 🎬 Garage Hollywood: ComfyUI Setup ---" -ForegroundColor Cyan

if (-not (Test-Path $ComfyPath)) {
    Write-Host "❌ ComfyUI path not found at $ComfyPath" -ForegroundColor Red
    $ComfyPath = Read-Host "Please enter the absolute path to your ComfyUI folder"
}

if (-not (Test-Path "$ComfyPath\custom_nodes")) {
    Write-Host "❌ Invalid ComfyUI path. custom_nodes folder missing." -ForegroundColor Red
    exit
}

# 1. Install Custom Nodes
Write-Host "📦 Installing Custom Nodes..." -ForegroundColor Yellow

$nodes = @(
    "https://github.com/ltdrdata/ComfyUI-Manager.git",
    "https://github.com/city96/ComfyUI-GGUF.git"
)

foreach ($node in $nodes) {
    $folderName = ($node -split "/")[-1].Replace(".git", "")
    $targetPath = "$ComfyPath\custom_nodes\$folderName"
    
    if (Test-Path $targetPath) {
        Write-Host "✅ $folderName already installed." -ForegroundColor Green
    } else {
        Write-Host "🚀 Cloning $folderName..." -ForegroundColor Cyan
        git clone $node $targetPath
    }
}

# 2. Check for Models
Write-Host "🔍 Checking for Flux GGUF Models..." -ForegroundColor Yellow

$models = @(
    @{ folder = "unet"; file = "flux1-schnell-Q4_K_S.gguf" },
    @{ folder = "vae"; file = "ae.safetensors" },
    @{ folder = "clip"; file = "clip_l.safetensors" },
    @{ folder = "clip"; file = "t5xxl_fp8_e4m3fn.safetensors" }
)

foreach ($m in $models) {
    $path = "$ComfyPath\models\$($m.folder)\$($m.file)"
    if (Test-Path $path) {
        Write-Host "✅ Found $($m.file) in $($m.folder)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Missing $($m.file) in $($m.folder)" -ForegroundColor Yellow
        Write-Host "   (You need to download this manually or use hf-cli)" -ForegroundColor Gray
    }
}

Write-Host "--- ✨ Setup Complete! ---" -ForegroundColor Green
Write-Host "Restart ComfyUI and then run your Garage Hollywood server."
