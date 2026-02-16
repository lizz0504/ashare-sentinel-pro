/**
 * LoadingSpinner Component
 * 统一的加载指示器组件
 */
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  text?: string;
}

export const LoadingSpinner = ({
  size = "md",
  className = "",
  text
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-2">
      <Loader2
        className={cn(sizeClasses[size], "animate-spin text-primary", className)}
      />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  );
};

/**
 * ErrorMessage Component
 * 统一的错误消息显示组件
 */
interface ErrorMessageProps {
  message: string;
  className?: string;
  onRetry?: () => void;
}

export const ErrorMessage = ({
  message,
  className = "",
  onRetry
}: ErrorMessageProps) => {
  return (
    <div className={`bg-destructive/10 border border-destructive rounded-md p-4 ${className}`}>
      <div className="flex items-start">
        <span className="text-destructive mr-2">⚠️</span>
        <div>
          <p className="font-medium text-destructive">发生错误</p>
          <p className="text-sm text-destructive/80 mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 text-sm underline text-destructive hover:text-destructive/80"
            >
              重试
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * SuccessMessage Component
 * 统一的成功消息显示组件
 */
interface SuccessMessageProps {
  message: string;
  className?: string;
}

export const SuccessMessage = ({
  message,
  className = ""
}: SuccessMessageProps) => {
  return (
    <div className={`bg-green-500/10 border border-green-500/30 rounded-md p-4 ${className}`}>
      <div className="flex items-start">
        <span className="text-green-500 mr-2">✓</span>
        <p className="text-green-500 font-medium">{message}</p>
      </div>
    </div>
  );
};