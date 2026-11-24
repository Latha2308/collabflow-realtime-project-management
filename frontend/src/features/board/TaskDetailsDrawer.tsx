import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { tasksApi } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { X, Trash2, Save, MessageSquare, Link2, AlertCircle } from 'lucide-react'
import type { Task, TaskStatus, TaskPriority, Comment, TaskDependency } from '@/types'
import { formatDateTime } from '@/lib/utils'

interface TaskDetailsDrawerProps {
  task: Task | null
  open: boolean
  onClose: () => void
  projectId: string
}

export default function TaskDetailsDrawer({ task, open, onClose, projectId }: TaskDetailsDrawerProps) {
  const queryClient = useQueryClient()
  const [editedTask, setEditedTask] = useState<Partial<Task>>({})
  const [newComment, setNewComment] = useState('')
  const [selectedDependencyTask, setSelectedDependencyTask] = useState('')
  const [dependencyError, setDependencyError] = useState('')

  useEffect(() => {
    if (task) {
      setEditedTask({
        title: task.title,
        description: task.description || '',
        status: task.status,
        priority: task.priority,
        due_date: task.due_date ? task.due_date.split('T')[0] : '',
        estimated_hours: task.estimated_hours || 0,
      })
      setSelectedDependencyTask('')
      setDependencyError('')
    }
  }, [task])

  const { data: comments = [] } = useQuery({
    queryKey: ['comments', task?.id],
    queryFn: () => tasksApi.listComments(task!.id),
    enabled: !!task?.id,
  })

  const { data: allTasks = [] } = useQuery<Task[]>({
    queryKey: ['tasks', projectId],
    queryFn: () => tasksApi.list(projectId),
    enabled: !!projectId,
  })

  const { data: dependencies = [] } = useQuery<TaskDependency[]>({
    queryKey: ['dependencies', projectId],
    queryFn: () => tasksApi.listDependencies(projectId),
    enabled: !!projectId,
  })

  // Get dependencies for current task
  const taskDependsOn = dependencies.filter(dep => dep.task_id === task?.id)
  const taskBlocking = dependencies.filter(dep => dep.depends_on_id === task?.id)

  // Get task details for dependencies
  const getTaskById = (taskId: string) => allTasks.find(t => t.id === taskId)

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Task>) => tasksApi.update(task!.id, { ...data, version: task!.version }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
      onClose()
    },
    onError: (error: { status?: number }) => {
      if (error.status === 409) {
        alert('Task was modified by another user. Please refresh and try again.')
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => tasksApi.delete(task!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
      onClose()
    },
  })

  const commentMutation = useMutation({
    mutationFn: (content: string) => tasksApi.createComment({ task_id: task!.id, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', task?.id] })
      setNewComment('')
    },
  })

  const addDependencyMutation = useMutation({
    mutationFn: (dependsOnId: string) => 
      tasksApi.createDependency({ task_id: task!.id, depends_on_id: dependsOnId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dependencies', projectId] })
      queryClient.invalidateQueries({ queryKey: ['graph-analysis', projectId] })
      setSelectedDependencyTask('')
      setDependencyError('')
    },
    onError: (error: { data?: { detail?: string } }) => {
      setDependencyError(error.data?.detail || 'Failed to add dependency')
    },
  })

  const removeDependencyMutation = useMutation({
    mutationFn: (dependencyId: string) => tasksApi.deleteDependency(dependencyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dependencies', projectId] })
      queryClient.invalidateQueries({ queryKey: ['graph-analysis', projectId] })
    },
  })

  const handleSave = () => {
    updateMutation.mutate(editedTask)
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this task?')) {
      deleteMutation.mutate()
    }
  }

  const handleAddComment = () => {
    if (newComment.trim()) {
      commentMutation.mutate(newComment)
    }
  }

  const handleAddDependency = () => {
    if (!selectedDependencyTask) return
    
    // Frontend validation
    if (selectedDependencyTask === task?.id) {
      setDependencyError('A task cannot depend on itself')
      return
    }

    // Check if dependency already exists
    const alreadyExists = taskDependsOn.some(dep => dep.depends_on_id === selectedDependencyTask)
    if (alreadyExists) {
      setDependencyError('This dependency already exists')
      return
    }

    setDependencyError('')
    addDependencyMutation.mutate(selectedDependencyTask)
  }

  const handleRemoveDependency = (dependencyId: string) => {
    if (confirm('Remove this dependency?')) {
      removeDependencyMutation.mutate(dependencyId)
    }
  }

  if (!open || !task) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      <div className="absolute right-0 top-0 bottom-0 w-full max-w-2xl bg-background shadow-xl overflow-y-auto">
        <div className="sticky top-0 bg-background border-b p-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Task Details</h2>
          <div className="flex gap-2">
            <Button variant="destructive" size="sm" onClick={handleDelete}>
              <Trash2 className="w-4 h-4 mr-1" />
              Delete
            </Button>
            <Button variant="outline" size="icon" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label className="text-sm font-medium mb-2 block">Title</label>
            <Input
              value={editedTask.title || ''}
              onChange={(e) => setEditedTask({ ...editedTask, title: e.target.value })}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium mb-2 block">Description</label>
            <Textarea
              value={editedTask.description || ''}
              onChange={(e) => setEditedTask({ ...editedTask, description: e.target.value })}
              rows={4}
            />
          </div>

          {/* Status and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select
                value={editedTask.status || ''}
                onChange={(e) => setEditedTask({ ...editedTask, status: e.target.value as TaskStatus })}
              >
                <option value="backlog">Backlog</option>
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="in_review">In Review</option>
                <option value="done">Done</option>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Priority</label>
              <Select
                value={editedTask.priority || ''}
                onChange={(e) => setEditedTask({ ...editedTask, priority: e.target.value as TaskPriority })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </Select>
            </div>
          </div>

          {/* Due Date and Estimated Hours */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Due Date</label>
              <Input
                type="date"
                value={editedTask.due_date || ''}
                onChange={(e) => setEditedTask({ ...editedTask, due_date: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Estimated Hours</label>
              <Input
                type="number"
                min="0"
                value={editedTask.estimated_hours || 0}
                onChange={(e) => setEditedTask({ ...editedTask, estimated_hours: parseInt(e.target.value) })}
              />
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              <Save className="w-4 h-4 mr-2" />
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>

          {/* Dependencies Section */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Link2 className="w-5 h-5" />
              Dependencies
            </h3>

            {/* Blocked By (Tasks this task depends on) */}
            <div className="mb-4">
              <h4 className="text-sm font-medium mb-2 text-muted-foreground">
                Blocked By ({taskDependsOn.length})
              </h4>
              {taskDependsOn.length > 0 ? (
                <div className="space-y-2">
                  {taskDependsOn.map(dep => {
                    const dependsOnTask = getTaskById(dep.depends_on_id)
                    return (
                      <div
                        key={dep.id}
                        className="flex items-center justify-between p-2 bg-muted rounded-lg"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium">
                            {dependsOnTask?.title || 'Unknown Task'}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Status: {dependsOnTask?.status || 'unknown'}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveDependency(dep.id)}
                          disabled={removeDependencyMutation.isPending}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  This task has no dependencies
                </p>
              )}
            </div>

            {/* Add New Dependency */}
            <div className="mb-4">
              <label className="text-sm font-medium mb-2 block">
                Add Dependency (this task depends on...)
              </label>
              <div className="flex gap-2">
                <Select
                  value={selectedDependencyTask}
                  onChange={(e) => {
                    setSelectedDependencyTask(e.target.value)
                    setDependencyError('')
                  }}
                  className="flex-1"
                >
                  <option value="">Select a task...</option>
                  {allTasks
                    .filter(t => t.id !== task?.id) // Filter out current task
                    .map(t => (
                      <option key={t.id} value={t.id}>
                        {t.title} ({t.status})
                      </option>
                    ))}
                </Select>
                <Button
                  onClick={handleAddDependency}
                  disabled={!selectedDependencyTask || addDependencyMutation.isPending}
                >
                  Add
                </Button>
              </div>
              {dependencyError && (
                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5" />
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {dependencyError}
                  </p>
                </div>
              )}
            </div>

            {/* Blocking (Tasks that depend on this task) */}
            <div>
              <h4 className="text-sm font-medium mb-2 text-muted-foreground">
                Blocking ({taskBlocking.length})
              </h4>
              {taskBlocking.length > 0 ? (
                <div className="space-y-2">
                  {taskBlocking.map(dep => {
                    const blockedTask = getTaskById(dep.task_id)
                    return (
                      <div
                        key={dep.id}
                        className="flex items-center justify-between p-2 bg-muted rounded-lg"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium">
                            {blockedTask?.title || 'Unknown Task'}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Status: {blockedTask?.status || 'unknown'}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No tasks are blocked by this task
                </p>
              )}
            </div>
          </div>

          {/* Comments Section */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Comments ({comments.length})
            </h3>

            <div className="space-y-4 mb-4">
              {comments.map((comment: Comment) => (
                <div key={comment.id} className="bg-muted p-3 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-medium text-sm">{comment.author_id}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(comment.created_at)}
                    </span>
                  </div>
                  <p className="text-sm">{comment.content}</p>
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <Textarea
                placeholder="Add a comment..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                rows={2}
              />
              <Button 
                onClick={handleAddComment} 
                disabled={!newComment.trim() || commentMutation.isPending}
              >
                Post
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
