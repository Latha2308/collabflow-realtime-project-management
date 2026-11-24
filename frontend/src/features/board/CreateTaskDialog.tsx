import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { tasksApi } from '@/services/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import type { Task, TaskStatus, TaskPriority } from '@/types'

interface CreateTaskDialogProps {
  open: boolean
  onClose: () => void
  projectId: string
}

export default function CreateTaskDialog({ open, onClose, projectId }: CreateTaskDialogProps) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string>('')
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'todo' as TaskStatus,
    priority: 'medium' as TaskPriority,
    due_date: '',
    estimated_hours: 0,
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<Task> & { title: string }) => 
      tasksApi.create({ ...data, project_id: projectId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', projectId] })
      setFormData({
        title: '',
        description: '',
        status: 'todo' as TaskStatus,
        priority: 'medium' as TaskPriority,
        due_date: '',
        estimated_hours: 0,
      })
      setError('')
      onClose()
    },
    onError: (err) => {
      const error = err as { response?: { data?: { detail?: string | { msg?: string }[] } } }
      const detail = error.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map(e => e.msg).join(', '))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Failed to create task. Please try again.')
      }
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (formData.title.trim()) {
      createMutation.mutate(formData)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md">
              {error}
            </div>
          )}
          
          <div>
            <label className="text-sm font-medium mb-2 block">Title *</label>
            <Input
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Task title"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Description</label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Task description"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as TaskStatus })}
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
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as TaskPriority })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Due Date</label>
              <Input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Estimated Hours</label>
              <Input
                type="number"
                min="0"
                value={formData.estimated_hours}
                onChange={(e) => setFormData({ ...formData, estimated_hours: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending || !formData.title.trim()}>
              {createMutation.isPending ? 'Creating...' : 'Create Task'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
