import { MetricCard } from "../MetricCard";
import type { ProjectSummary } from "../../hooks/useProjectExpenses";
import type { Project } from "../../hooks/useProjects";

interface Props {
  summary: ProjectSummary | undefined;
  project: Project | undefined;
  isLoading: boolean;
}

export function ProjectSummaryCards({ summary, project, isLoading }: Props) {
  if (isLoading || !summary) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 animate-pulse h-20" />
        ))}
      </div>
    );
  }

  const topCategory = Object.entries(summary.category_totals).sort(
    ([, a], [, b]) => b - a
  )[0];

  const budgetDelta =
    project?.budget != null ? project.budget - summary.total_paid : undefined;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard
        label="Total Spent"
        value={summary.total_paid}
        color="gold"
      />
      <MetricCard
        label="Budget"
        value={project?.budget ?? 0}
        prefix={project?.budget != null ? "\u20B9" : ""}
        suffix={project?.budget == null ? "" : undefined}
        delta={budgetDelta}
        deltaLabel="remaining"
        color={budgetDelta != null && budgetDelta < 0 ? "warning" : "default"}
      />
      <MetricCard
        label="Top Category"
        value={topCategory ? topCategory[1] : 0}
        suffix={topCategory ? ` (${topCategory[0]})` : ""}
        color="success"
      />
      <MetricCard
        label="Entries"
        value={summary.entry_count}
        prefix=""
        color="default"
      />
    </div>
  );
}
