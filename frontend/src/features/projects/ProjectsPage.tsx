import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { projectsApi } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Plus, FolderKanban, BarChart3 } from 'lucide-react'
import type { Project } from '@/types'

export default function ProjectsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects', workspaceId],
    queryFn: () => projectsApi.list(workspaceId!),
    enabled: !!workspaceId,
  })

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', workspaceId] })
      setShowCreate(false)
      setName('')
      setDescription('')
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ workspace_id: workspaceId!, name, description })
  }

  if (isLoading) {
    return <div>Loading projects...</div>
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground mt-1">Manage projects in this workspace</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="w-4 h-4 mr-2" />
          Create Project
        </Button>
      </div>

      {showCreate && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create New Project</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Project"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  Create
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects?.map((project: Project) => (
          <Card key={project.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <FolderKanban className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    {project.description && (
                      <CardDescription className="mt-1">{project.description}</CardDescription>
                    )}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Link to={`/projects/${project.id}/board`} className="flex-1">
                  <Button variant="outline" className="w-full">
                    <FolderKanban className="w-4 h-4 mr-2" />
                    Board
                  </Button>
                </Link>
                <Link to={`/projects/${project.id}/analytics`} className="flex-1">
                  <Button variant="outline" className="w-full">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Analytics
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {projects?.length === 0 && (
        <div className="text-center py-12">
          <FolderKanban className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            No projects yet
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Create your first project to start managing tasks
          </p>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Project
          </Button>
        </div>
      )}
    </div>
  )
}
