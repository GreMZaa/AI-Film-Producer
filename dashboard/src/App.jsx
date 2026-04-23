import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Film, Cpu, HardDrive, Play, Zap, Settings, Activity } from 'lucide-react';
import './App.css';

const App = () => {
  const [stats, setStats] = useState({
    movies: 12,
    renderTime: '4m 12s',
    gpuUsage: '68%',
    storage: '4.2 GB'
  });

  const [productions, setProductions] = useState([
    { id: 1, title: 'Neon Despair', date: '2024-04-23', status: 'Completed' },
    { id: 2, title: 'The Last Can', date: '2024-04-22', status: 'Completed' },
    { id: 3, title: 'Indie Coffee', date: '2024-04-21', status: 'Completed' },
  ]);

  return (
    <div className="dashboard-container">
      <header>
        <div className="logo-section">
          <h1>GARAGE HOLLYWOOD</h1>
          <p>AI Film Producer Control Center</p>
        </div>
        <div className="status-badge">
          <div className="status-dot pulse"></div>
          STUDIO ONLINE
        </div>
      </header>

      <main>
        <div className="grid-layout">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card"
          >
            <div className="card-title">
              <Film size={20} />
              Total Productions
            </div>
            <div className="stat-value">{stats.movies}</div>
            <div className="stat-label">Masterpieces completed</div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card"
          >
            <div className="card-title">
              <Zap size={20} />
              Avg. Render Speed
            </div>
            <div className="stat-value">{stats.renderTime}</div>
            <div className="stat-label">Per 3-scene project</div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="card"
          >
            <div className="card-title">
              <Cpu size={20} />
              GPU Load
            </div>
            <div className="stat-value">{stats.gpuUsage}</div>
            <div className="stat-label">NVIDIA RTX 4090</div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="card"
          >
            <div className="card-title">
              <HardDrive size={20} />
              Storage
            </div>
            <div className="stat-value">{stats.storage}</div>
            <div className="stat-label">Asset library size</div>
          </motion.div>
        </div>

        <section className="movie-gallery">
          <div className="card-title">
            <Activity size={20} />
            Latest Productions
          </div>
          <div className="movie-grid">
            {productions.map((prod, index) => (
              <motion.div 
                key={prod.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 + index * 0.1 }}
                className="movie-item"
              >
                <div className="movie-overlay">
                  <div className="movie-title">{prod.title}</div>
                  <div className="movie-date">{prod.date}</div>
                  <button className="btn-primary" style={{ marginTop: '10px', padding: '5px 10px', fontSize: '0.7rem' }}>
                    <Play size={12} style={{ marginRight: '5px' }} />
                    Play
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};

export default App;
