import React, { useRef, useEffect, useState } from 'react';

const DirectorCanvas = ({ imageUrl, onSave, brushSize = 20 }) => {
  const canvasRef = useRef(null);
  const maskCanvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [ctx, setCtx] = useState(null);
  const [maskCtx, setMaskCtx] = useState(null);
  const [image, setImage] = useState(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const maskCanvas = maskCanvasRef.current;
    const context = canvas.getContext('2d');
    const mContext = maskCanvas.getContext('2d');
    
    setCtx(context);
    setMaskCtx(mContext);

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = imageUrl;
    img.onload = () => {
      // Set canvas size to match image aspect ratio while fitting container
      const containerWidth = canvas.parentElement.clientWidth;
      const scale = containerWidth / img.width;
      canvas.width = containerWidth;
      canvas.height = img.height * scale;
      maskCanvas.width = canvas.width;
      maskCanvas.height = canvas.height;

      context.drawImage(img, 0, 0, canvas.width, canvas.height);
      setImage(img);
      
      // Initialize mask to black (transparent in our logic, but we'll draw white for mask)
      mContext.fillStyle = 'black';
      mContext.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
    };
  }, [imageUrl]);

  const startDrawing = (e) => {
    setIsDrawing(true);
    draw(e);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
    ctx.beginPath();
    maskCtx.beginPath();
  };

  const draw = (e) => {
    if (!isDrawing) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX || e.touches[0].clientX) - rect.left;
    const y = (e.clientY || e.touches[0].clientY) - rect.top;

    // Draw on main canvas (semi-transparent red for visual feedback)
    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);

    // Draw on mask canvas (white for mask area)
    maskCtx.lineWidth = brushSize;
    maskCtx.lineCap = 'round';
    maskCtx.strokeStyle = 'white';
    maskCtx.lineTo(x, y);
    maskCtx.stroke();
    maskCtx.beginPath();
    maskCtx.moveTo(x, y);
  };

  const handleExport = () => {
    const maskBase64 = maskCanvasRef.current.toDataURL('image/png');
    onSave(maskBase64);
  };

  const clearCanvas = () => {
    if (!image) return;
    ctx.drawImage(image, 0, 0, canvasRef.current.width, canvasRef.current.height);
    maskCtx.fillStyle = 'black';
    maskCtx.fillRect(0, 0, maskCanvasRef.current.width, maskCanvasRef.current.height);
  };

  return (
    <div className="canvas-container" style={{ position: 'relative', width: '100%', maxWidth: '1000px', margin: '0 auto' }}>
      <canvas
        ref={canvasRef}
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseOut={stopDrawing}
        onTouchStart={startDrawing}
        onTouchMove={draw}
        onTouchEnd={stopDrawing}
        style={{ 
            cursor: 'crosshair', 
            borderRadius: '12px', 
            boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            touchAction: 'none'
        }}
      />
      <canvas ref={maskCanvasRef} style={{ display: 'none' }} />
      
      <div className="canvas-toolbar" style={{ marginTop: '1rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <button onClick={clearCanvas} className="btn-secondary">Очистить</button>
        <button onClick={handleExport} className="btn-primary">Применить маску</button>
      </div>
    </div>
  );
};

export default DirectorCanvas;
