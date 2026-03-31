interface EmptyStateProps {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ message, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <p className="text-[#E8ECF1]/60 mb-4">{message}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-6 py-2 bg-[#00895E] text-white rounded-lg hover:bg-[#00895E]/80 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
