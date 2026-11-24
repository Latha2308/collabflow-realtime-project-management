import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Clock, AlertCircle } from 'lucide-react'
import type { Task } from '@/types'
import { formatDate, isOverdue } from '@/lib/utils'

interface TaskCardProps {
  task: Task
  isDragging?: boolean
  onClick?: () => void
}

export default function TaskCard({ task, isDragging, onClick }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const priorityColors = {
    urgent: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400',
    medium: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
    low: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="p-4 cursor-pointer hover:shadow-md transition-shadow touch-none"
    >
      <div className="space-y-3">
        <h4 className="font-medium text-sm">{task.title}</h4>
        
        {task.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {task.description}
          </p>
        )}

        <div className="flex items-center justify-between gap-2 flex-wrap">
          <Badge className={priorityColors[task.priority]}>
            {task.priority}
          </Badge>

          {task.due_date && (
            <div className={`flex items-center gap-1 text-xs ${
              isOverdue(task.due_date) ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'
            }`}>
              {isOverdue(task.due_date) && <AlertCircle className="w-3 h-3" />}
              <Clock className="w-3 h-3" />
              <span>{formatDate(task.due_date)}</span>
            </div>
          )}
        </div>

        {task.estimated_hours && (
          <div className="text-xs text-muted-foreground">
            Est: {task.estimated_hours}h
          </div>
        )}
      </div>
    </Card>
  )
}
