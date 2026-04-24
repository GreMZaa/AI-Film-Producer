import React, { useState, useEffect } from 'react';
import DirectorCanvas from './components/DirectorCanvas';
import axios from 'axios';
import './App.css';

function App() {
  const [imageUrl, setImageUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('idle'); // idle, processing, success, error
  const [sceneId, setSceneId] = useState(null);
  const [userId, setUserId] = useState(null);
  const [userStatus, setUserStatus] = useState({ is_premium: false, subscription_type: null });

  useEffect(() => {
    // Get parameters from URL (passed by the bot)
    const params = new URLSearchParams(window.location.search);
    const img = params.get('image_url');
    const sid = params.get('scene_id');
    if (uid) {
      setUserId(parseInt(uid));
      fetchUserStatus(parseInt(uid));
    } else if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe.user) {
      const telegramUserId = window.Telegram.WebApp.initDataUnsafe.user.id;
      setUserId(telegramUserId);
      fetchUserStatus(telegramUserId);
    }

    // Initialize Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  }, []);

  const fetchUserStatus = async (uid) => {
    try {
      const response = await axios.get(`/api/user-status/${uid}`);
      setUserStatus(response.data);
    } catch (error) {
      console.error("Failed to fetch user status:", error);
    }
  };

  const handleInpaint = async (maskBase64) => {
    if (!prompt) {
      alert("Напишите, что нужно изменить в закрашенной области!");
      return;
    }

    setStatus('processing');
    try {
      const response = await axios.post('/api/inpainting', {
        image_url: imageUrl,
        mask_base64: maskBase64,
        prompt: prompt,
        scene_id: sceneId,
        user_id: userId
      });

      if (response.data && response.data.image_url) {
        setStatus('success');
        setImageUrl(response.data.image_url);
        // Notify Telegram that we are done or just show success
        if (window.Telegram && window.Telegram.WebApp) {
          window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        }
      }
    } catch (error) {
      console.error("Inpainting failed:", error);
      setStatus('error');
      if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
      }
    }
  };

  return (
    <div className="app-container">
      <header className="premium-header">
        <h1>🎬 Режиссерская правка</h1>
        <p>Закрасьте область и опишите изменения</p>
      </header>

      <main className="editor-main">
        {!userStatus.is_premium ? (
          <div className="premium-lock">
            <div className="lock-icon">🔒</div>
            <h2>Доступ ограничен</h2>
            <p>Функция Inpainting доступна только для продюсеров со статусом <b>Indie Premiere</b>.</p>
            <p>Вернись в бота и введи /upgrade, чтобы разблокировать правки.</p>
          </div>
        ) : imageUrl ? (
          <DirectorCanvas imageUrl={imageUrl} onSave={handleInpaint} />
        ) : (
          <div className="loader">Загрузка кадра...</div>
        )}

        <div className="prompt-section">
          <label htmlFor="prompt">Что изменить?</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Например: 'замени стакан на бутылку виски' или 'сделай лицо более злым'"
            rows="3"
          />
        </div>

        {status === 'processing' && (
          <div className="status-overlay">
            <div className="spinner"></div>
            <p>Перерисовываю шедевр...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="success-msg">
            <p>✅ Готово! Можешь закрыть окно или продолжить правки.</p>
          </div>
        )}

        {status === 'error' && (
          <div className="error-msg">
            <p>❌ Ошибка рендера. Попробуй еще раз или напиши админу.</p>
            <button onClick={() => setStatus('idle')}>Ок</button>
          </div>
        )}
      </main>

      <footer className="premium-footer">
          <button onClick={() => window.Telegram?.WebApp.close()} className="btn-close">
              Вернуться в бот
          </button>
      </footer>
    </div>
  );
}

export default App;
