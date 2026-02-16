"use client"

import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DrawerProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
  className?: string
}

interface DrawerContentProps {
  children: React.ReactNode
  className?: string
}

interface DrawerHeaderProps {
  children: React.ReactNode
  className?: string
}

interface DrawerBodyProps {
  children: React.ReactNode
  className?: string
}

export function Drawer({ open, onOpenChange, children, className }: DrawerProps) {
  const [internalOpen, setInternalOpen] = React.useState(open ?? false)
  const isOpen = open !== undefined ? open : internalOpen

  const handleOpenChange = (newOpen: boolean) => {
    if (onOpenChange) {
      onOpenChange(newOpen)
    } else {
      setInternalOpen(newOpen)
    }
  }

  React.useEffect(() => {
    if (open !== undefined) {
      setInternalOpen(open)
    }
  }, [open])

  // Prevent body scroll when drawer is open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [isOpen])

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
          onClick={() => handleOpenChange(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-full max-w-md transform transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {children}
      </div>
    </>
  )
}

export function DrawerContent({ children, className }: DrawerContentProps) {
  return (
    <div className={cn("h-full flex flex-col bg-slate-900 border-l border-slate-700", className)}>
      {children}
    </div>
  )
}

export function DrawerHeader({ children, className }: DrawerHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between px-6 py-4 border-b border-slate-700", className)}>
      {children}
    </div>
  )
}

export function DrawerBody({ children, className }: DrawerBodyProps) {
  return (
    <div className={cn("flex-1 overflow-y-auto px-6 py-4", className)}>
      {children}
    </div>
  )
}

export function DrawerTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-lg font-semibold text-slate-100", className)}>
      {children}
    </h2>
  )
}

export function DrawerClose({ onClick }: { onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-sm opacity-70 ring-offset-slate-900 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-slate-800 data-[state=open]:text-slate-200"
    >
      <X className="h-4 w-4 text-slate-400" />
      <span className="sr-only">Close</span>
    </button>
  )
}
