import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

const classNames = (...classes) => classes.filter(Boolean).join(' ');

const CheckIcon = ({ className }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className={classNames('w-6 h-6', className)}
    >
      <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
};

const CheckFilled = ({ className }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={classNames('w-6 h-6', className)}
    >
      <path
        fillRule="evenodd"
        d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
        clipRule="evenodd"
      />
    </svg>
  );
};

const LoaderCore = ({ loadingStates, value = 0 }) => {
  return (
    <div className="flex flex-col space-y-4">
      {loadingStates.map((loadingState, index) => {
        const distance = Math.abs(index - value);
        const opacity = Math.max(1 - distance * 0.2, 0);

        return (
          <motion.div
            key={index}
            className={classNames('flex gap-2 items-center')}
            initial={{ opacity: 0, y: -(value * 40) }}
            animate={{ opacity: opacity, y: -(value * 40) }}
            transition={{ duration: 0.5 }}
          >
            <div>
              {index > value && (
                <CheckIcon className="text-gray-500 dark:text-gray-400" />
              )}
              {index <= value && (
                <CheckFilled
                  className={classNames(
                    'text-gray-500 dark:text-gray-400',
                    value === index && 'text-green-600 dark:text-green-400 opacity-100'
                  )}
                />
              )}
            </div>
            <span
              className={classNames(
                'text-sm font-medium text-gray-500 dark:text-gray-400',
                value === index && 'text-green-600 dark:text-green-400 opacity-100'
              )}
            >
              {loadingState.text}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
};

const Loading = ({ loadingStates, duration = 2000, loop = true }) => {
  const [currentState, setCurrentState] = useState(0);

  useEffect(() => {
    if (!loadingStates.length) {
      setCurrentState(0);
      return;
    }
    const timeout = setTimeout(() => {
      setCurrentState((prevState) =>
        loop
          ? prevState === loadingStates.length - 1
            ? 0
            : prevState + 1
          : Math.min(prevState + 1, loadingStates.length - 1)
      );
    }, duration);

    return () => clearTimeout(timeout);
  }, [currentState, loadingStates, duration, loop]);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="w-full h-full fixed inset-0 z-[100] flex items-center justify-center bg-gray-50/80 dark:bg-gray-900/80 backdrop-blur-lg transition-colors duration-200"
      >
        <div className="max-w-7xl mx-auto mt-20">
          <LoaderCore value={currentState} loadingStates={loadingStates} />
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default Loading;