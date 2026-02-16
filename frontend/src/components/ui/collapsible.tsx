"use client"

import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface CollapsibleProps {
  children: React.ReactNode
  defaultOpen?: boolean
  open?: boolean
  onOpenChange?: (open: boolean) => void
  className?: string
}

interface CollapsibleTriggerProps {
  children: React.ReactNode
  className?: string
}

interface CollapsibleContentProps {
  children: React.ReactNode
  className?: string
}

export function Collapsible({ children, defaultOpen = false, open, onOpenChange, className }: CollapsibleProps) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen)
  const isOpen = open !== undefined ? open : internalOpen

  const handleToggle = () => {
    const newOpen = !isOpen
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

  // Provide context for children
  const context = { isOpen, onToggle: handleToggle }

  return (
    <div className={cn("w-full", className)}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as any, { context } as any)
        }
        return child
      })}
    </div>
  )
}

export function CollapsibleTrigger({ children, className }: CollapsibleTriggerProps) {
  const context: any = React.useContext(CollapsibleContext)

  return (
    <CollapsibleContext.Consumer>
      {(ctx: any) => (
        <button
          onClick={ctx?.onToggle}
          className={cn(
            "flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 rounded-lg transition-colors",
            className
          )}
        >
          {children}
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform duration-200",
              ctx?.isOpen && "rotate-180"
            )}
          />
        </button>
      )}
    </CollapsibleContext.Consumer>
  )
}

export function CollapsibleContent({ children, className }: CollapsibleContentProps) {
  const context: any = React.useContext(CollapsibleContext)

  return (
    <CollapsibleContext.Consumer>
      {(ctx: any) => (
        <div
          className={cn(
            "overflow-hidden transition-all duration-300 ease-in-out",
            ctx?.isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
            className
          )}
        >
          <div className="py-2">{children}</div>
        </div>
      )}
    </CollapsibleContext.Consumer>
  )
}

// Context
const CollapsibleContext = React.createContext<{
  isOpen: boolean
  onToggle: () => void
} | null>(null)
