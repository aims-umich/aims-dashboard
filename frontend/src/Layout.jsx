import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { FiMoon, FiSun } from 'react-icons/fi';
import { Sidebar } from './components/Sidebar';

const Layout = () => {
  const [darkMode, setDarkMode] = useState(() => {
    const savedMode = localStorage.getItem('darkMode');
    return savedMode ? JSON.parse(savedMode) : true;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
  }, [darkMode]);

  return (
    <Sidebar>
      <div className="p-4">
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white"
            aria-label={darkMode ? 'Switch to Light Mode.' : 'Switch to Dark Mode.'}
          >
            {darkMode ? <FiSun className="w-5 h-5" /> : <FiMoon className="w-5 h-5" />}
          </button>
        </div>
        <Outlet />
      </div>
    </Sidebar>
  );
};

export default Layout;