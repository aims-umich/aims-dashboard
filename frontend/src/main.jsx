import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import App from './App';
import Threads from './components/Threads'
import Mastodon from './components/Mastodon'
import Reddit from './components/Reddit'
import YouTube from './components/YouTube'
import Guardian from './components/Guardian'
import Times from './components/Times'
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<App />} />
          <Route path="/instagram" element={<Threads />} />
          <Route path="/mastodon" element={<Mastodon />} />
          <Route path="/reddit" element={<Reddit />} />
          <Route path="/youtube" element={<YouTube />}/>
          <Route path="/guardian" element={<Guardian />} />
          <Route path="/times" element={<Times />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);