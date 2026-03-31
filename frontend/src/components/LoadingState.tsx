export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#00895E] mr-3"></div>
      <span className="text-[#E8ECF1]/60">{message}</span>
    </div>
  );
}
