import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { SidebarImpl, SidebarBody, SidebarLink } from './ui/SidebarImpl';
import { BookOpen, NewspaperIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { classNames } from '../lib/utils';
import { SocialIcon } from 'react-social-icons';

export function Sidebar({ children }) {
  const links = [
    {
      label: 'Instagram Threads',
      href: '/instagram',
      icon: (
        <SocialIcon network="threads" className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" style={{ height: 25, width: 25 }}/>
      ),
    },
    {
      label: 'Mastodon',
      href: '/mastodon',
      icon: (
        <SocialIcon network="mastodon" className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" style={{ height: 25, width: 25 }}/>
      ),
    },
    {
      label: 'Reddit',
      href: '/reddit',
      icon: (
        <SocialIcon network="reddit" className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" style={{ height: 25, width: 25 }}/>
      ),
    },
    {
      label: 'YouTube',
      href: '/youtube',
      icon: (
        <SocialIcon network="youtube" className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" style={{ height: 25, width: 25 }}/>
      ),
    },
    {
      label: 'The Guardian',
      href: '/guardian',
      icon: (
        <BookOpen />
      ),
    },
    {
      label: 'New York Times',
      href: '/times',
      icon: (
        <NewspaperIcon />
      ),
    },
  ];

  const [open, setOpen] = useState(false);

  return (
    <div
      className={classNames(
        'flex flex-col md:flex-row bg-gray-50 dark:bg-gray-900 w-full h-screen overflow-hidden'
      )}
    >
      <SidebarImpl open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-10">
          <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
            {open ? <Logo /> : <LogoIcon />}
            <div className="mt-8 flex flex-col gap-2">
              {links.map((link, idx) => (
                <SidebarLink key={idx} link={link} />
              ))}
            </div>
          </div>
          <div>
            <SidebarLink
              link={{
                label: 'AIMS 2025',
                href: '#',
                icon: (
                  <img
                    src="/michigan.webp"
                    className="h-7 w-7 rounded-full"
                    width={50}
                    height={50}
                    alt="Michigan M"
                  />
                ),
              }}
            />
          </div>
        </SidebarBody>
      </SidebarImpl>
      <div className={classNames(
        'flex-1 overflow-y-auto transition-all duration-300',
        open ? 'md:ml-[300px]' : 'md:ml-16'
      )}>
        {children}
      </div>
    </div>
  );
}

export const Logo = () => {
  return (
    <Link
      to="/"
      className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
    >
      <div className="h-5 w-6 bg-black dark:bg-white rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm flex-shrink-0" />
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="font-medium text-black dark:text-white whitespace-pre"
      >
        Dashboard
      </motion.span>
    </Link>
  );
};

export const LogoIcon = () => {
  return (
    <Link
      to="/"
      className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
    >
      <div className="h-5 w-6 bg-black dark:bg-white rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm flex-shrink-0" />
    </Link>
  );
};
