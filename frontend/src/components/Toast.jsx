import { useState, useEffect } from 'react'

export default function Toast({ message, type, onClose }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (message) {
      setShow(true)
      const timer = setTimeout(() => {
        setShow(false)
        if (onClose) onClose()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [message, onClose])

  if (!message) return null

  return (
    <div className={`toast toast-${type || 'info'} ${show ? 'show' : ''}`} role="alert" aria-live="polite">
      {message}
    </div>
  )
}
