interface PageHeaderProps {
  title: string;
  subtitle?: string;
}

export function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-[#E8ECF1]">{title}</h1>
      {subtitle && <p className="text-[#E8ECF1]/60 mt-1">{subtitle}</p>}
    </div>
  );
}
