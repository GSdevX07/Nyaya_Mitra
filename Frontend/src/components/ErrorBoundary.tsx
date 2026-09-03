import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          aria-live="assertive"
          className="min-h-screen flex items-center justify-center bg-background p-6"
        >
          <div className="max-w-md w-full bg-card border-2 border-destructive/30 rounded-2xl p-8 shadow-2xl space-y-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-destructive/10 border border-destructive/20 flex items-center justify-center text-destructive mx-auto">
              <AlertTriangle className="w-8 h-8" aria-hidden="true" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-serif font-black text-foreground">
                {this.props.fallbackTitle || "Something went wrong"}
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed">
                An unexpected interface exception occurred. Your legal session and recorded decisions in the database remain safe and intact.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3 bg-secondary/50 rounded-xl text-left overflow-x-auto max-h-32 border border-border">
                <div className="text-[11px] font-mono text-destructive font-semibold">
                  {this.state.error.name}: {this.state.error.message}
                </div>
              </div>
            )}

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-bold rounded-xl flex items-center gap-2 hover:opacity-90 transition-opacity shadow-md shadow-primary/20"
                aria-label="Reload Application"
              >
                <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> Reload Page
              </button>
              <button
                onClick={this.handleGoHome}
                className="px-4 py-2 bg-secondary text-foreground text-xs font-bold rounded-xl flex items-center gap-2 hover:bg-secondary/80 border border-border transition-colors"
                aria-label="Return to Landing Page"
              >
                <Home className="w-3.5 h-3.5" aria-hidden="true" /> Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
