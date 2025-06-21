'use client'


import React from 'react'

export default function Icon() {
  return (
    <img
      src="/media/vale-logo.svg"
      alt="Vale"
      style={{
        width: '32px',
        height: '32px',
        objectFit: 'contain',
        display: 'block',
      }}
      onError={(e) => {
        console.error('Failed to load icon image:', e)
        e.currentTarget.style.display = 'none'
      }}
      onLoad={() => {
        console.log('Icon image loaded successfully')
      }}
    />
  )
}