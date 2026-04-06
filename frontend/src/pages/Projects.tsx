import { useState, useMemo } from "react";
import { Plus } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { ProjectSummaryCards } from "../components/projects/ProjectSummaryCards";
import { ProjectExpenseQuickAdd } from "../components/projects/ProjectExpenseQuickAdd";
import { ProjectExpenseTable } from "../components/projects/ProjectExpenseTable";
import { ProjectCharts } from "../components/projects/ProjectCharts";
import { useProjects } from "../hooks/useProjects";
import { useProjectExpenses, useProjectSummary } from "../hooks/useProjectExpenses";

export default function Projects() {
  const { projects, isLoading: projectsLoading, save: saveProject } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectBudget, setNewProjectBudget] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);

  // Auto-select first project
  const activeProjectId = selectedProjectId || projects[0]?.id || "";

  const { expenses, isLoading: expensesLoading, save: saveExpense, update: updateExpense, deactivate: deactivateExpense } =
    useProjectExpenses({ projectId: activeProjectId });

  const { data: summary, isLoading: summaryLoading } = useProjectSummary(activeProjectId);

  const activeProject = projects.find((p) => p.id === activeProjectId);

  const categories = useMemo(() => {
    const cats = new Set(expenses.map((e) => e.category));
    return Array.from(cats).sort();
  }, [expenses]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    try {
      await saveProject({
        name: newProjectName.trim(),
        status: "active",
        budget: newProjectBudget ? parseFloat(newProjectBudget) : null,
        start_date: new Date().toISOString().slice(0, 10),
        end_date: null,
      });
      setNewProjectName("");
      setNewProjectBudget("");
      setShowNewProject(false);
    } finally {
      setCreatingProject(false);
    }
  };

  if (projectsLoading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Projects" subtitle="Track expenses for construction, renovation, and other projects" />

      {/* Project selector + New Project */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={activeProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
          className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded-lg px-4 py-2 text-sm text-[#E8ECF1] min-w-[200px]"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {p.status === "completed" ? "(Completed)" : ""}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowNewProject(!showNewProject)}
          className="flex items-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* New project form */}
      {showNewProject && (
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Project Name</label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="e.g. Car Purchase"
                maxLength={100}
                className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Budget (optional)</label>
              <input
                type="number"
                value={newProjectBudget}
                onChange={(e) => setNewProjectBudget(e.target.value)}
                placeholder="Total budget"
                min="1"
                className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] w-40"
              />
            </div>
            <button
              onClick={handleCreateProject}
              disabled={creatingProject || !newProjectName.trim()}
              className="bg-[#D4A843] hover:bg-[#D4A843]/80 text-[#0D1B2A] rounded px-4 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {creatingProject ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      {/* No projects state */}
      {projects.length === 0 && !showNewProject && (
        <EmptyState
          message="No projects yet — create a project to start tracking expenses"
        />
      )}

      {/* Project content */}
      {activeProjectId && (
        <>
          <ProjectSummaryCards
            summary={summary}
            project={activeProject}
            isLoading={summaryLoading}
          />

          <ProjectExpenseQuickAdd
            projectId={activeProjectId}
            categories={categories}
            onSave={saveExpense}
          />

          {expensesLoading ? (
            <LoadingState />
          ) : (
            <ProjectExpenseTable
              expenses={expenses}
              categories={categories}
              onUpdate={updateExpense}
              onDeactivate={deactivateExpense}
            />
          )}

          <ProjectCharts summary={summary} />
        </>
      )}
    </div>
  );
}
