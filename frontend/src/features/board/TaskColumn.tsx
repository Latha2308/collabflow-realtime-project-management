import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { cn } from '@/lib/utils'
import type { Task, TaskStatus } from '@/types'
import TaskCard from './TaskCard'

interface TaskColumnProps {
  id: TaskStatus
  title: string
  tasks: Task[]
  onTaskClick: (task: Task) => void
}

export default function TaskColumn({ id, title, tasks, onTaskClick }: TaskColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <div className="flex-1 flex flex-col min-w-[280px]">
      <div className={cn(
        "mb-4 px-4 py-3 rounded-lg transition-colors",
        "bg-gray-100 dark:bg-gray-800",
        isOver && "bg-gray-200 dark:bg-gray-700"
      )}>
        <h3 className="font-semibold text-sm">{title}</h3>
        <span className="text-xs text-muted-foreground">
          {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
        </span>
      </div>

      <div
        ref={setNodeRef}
        className={cn(
          "flex-1 space-y-3 overflow-y-auto p-2 rounded-lg transition-colors",
          isOver && "bg-gray-50 dark:bg-gray-900/50"
        )}
      >
        <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => onTaskClick(task)}
            />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div className="text-center py-8 text-sm text-muted-foreground">
            No tasks
          </div>
        )}
      </div>
    </div>
  )
}
