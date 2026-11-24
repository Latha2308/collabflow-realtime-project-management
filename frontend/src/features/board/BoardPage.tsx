import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, closestCorners, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { tasksApi } from '@/services/api'
import { wsService } from '@/services/websocket'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { TaskStatus, type Task } from '@/types'
import TaskCard from './TaskCard'
import TaskColumn from './TaskColumn'
import TaskDetailsDrawer from './TaskDetailsDrawer'
import CreateTaskDialog from './CreateTaskDialog'

export default function BoardPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const [activeId, setActiveId] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  )

  // Fetch tasks
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks', projectId],
    queryFn: () => tasksApi.list(projectId!),
    enabled: !!projectId,
  })

  // WebSocket setup
  useEffect(() => {
    if (!projectId) return

    const setupWebSocket = async () => {
      try {
        wsService.connect(projectId)
        
        const unsubscribe = wsService.onMessage((message) => {
          if (['task_created', 'task_updated', 'task_deleted', 'task_moved'].includes(message.type)) {
            queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
          }
        })

        return () => {
          unsubscribe()
          wsService.disconnect()
        }
      } catch (error) {
        console.error('WebSocket setup failed:', error)
      }
    }

    setupWebSocket()
  }, [projectId, queryClient])

  const updateTaskMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Task> }) => tasksApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: ['tasks', projectId] })
      const previousTasks = queryClient.getQueryData<Task[]>(['tasks', projectId])
      
      queryClient.setQueryData<Task[]>(['tasks', projectId], (old) =>
        old?.map(task => task.id === id ? { ...task, ...data, version: task.version + 1 } : task) || []
      )

      wsService.send({
        type: 'task_moved',
        data: { task_id: id, ...data }
      })

      return { previousTasks }
    },
    onError: (_err, _variables, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(['tasks', projectId], context.previousTasks)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
    },
  })

  const columns = [
    { id: TaskStatus.BACKLOG, title: 'Backlog' },
    { id: TaskStatus.TODO, title: 'To Do' },
    { id: TaskStatus.IN_PROGRESS, title: 'In Progress' },
    { id: TaskStatus.IN_REVIEW, title: 'In Review' },
    { id: TaskStatus.DONE, title: 'Done' },
  ]

  const getTasksByStatus = (status: TaskStatus) => {
    return tasks.filter((task: Task) => task.status === status).sort((a: Task, b: Task) => a.position - b.position)
  }

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    
    if (!over) {
      setActiveId(null)
      return
    }

    const activeTask = tasks.find((t: Task) => t.id === active.id)
    const overColumn = over.id as TaskStatus

    if (activeTask && activeTask.status !== overColumn) {
      updateTaskMutation.mutate({
        id: activeTask.id,
        data: {
          status: overColumn,
          version: activeTask.version
        }
      })
    }

    setActiveId(null)
  }

  const activeTask = activeId ? tasks.find((t: Task) => t.id === activeId) : null

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg">Loading board...</div>
      </div>
    )
  }

  return (
    <>
      <div className="h-full flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Kanban Board</h1>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Task
          </Button>
        </div>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex-1 overflow-x-auto">
            <div className="flex gap-4 h-full" style={{ minWidth: '1200px' }}>
              {columns.map((column) => (
                <TaskColumn
                  key={column.id}
                  id={column.id}
                  title={column.title}
                  tasks={getTasksByStatus(column.id)}
                  onTaskClick={setSelectedTask}
                />
              ))}
            </div>
          </div>

          <DragOverlay>
            {activeTask ? <TaskCard task={activeTask} isDragging /> : null}
          </DragOverlay>
        </DndContext>
      </div>

      <TaskDetailsDrawer
        task={selectedTask}
        open={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        projectId={projectId!}
      />

      <CreateTaskDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        projectId={projectId!}
      />
    </>
  )
}
