'use client'

import React from 'react'

export default function Logo() {
  return (
    <img
      src="/media/vale-core-banner.svg"
      alt="Vale LMS"
      style={{
        maxHeight: '80px',
        width: 'auto',
        objectFit: 'contain',
        display: 'block',
      }}
      onError={(e) => {
        console.error('Failed to load logo image:', e)
        e.currentTarget.style.display = 'none'
      }}
      onLoad={() => {
        console.log('Logo image loaded successfully')
      }}
    />
  )
}
