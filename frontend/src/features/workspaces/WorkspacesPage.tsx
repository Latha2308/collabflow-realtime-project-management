import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { workspacesApi } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Plus, Briefcase } from 'lucide-react'
import type { Workspace } from '@/types'

export default function WorkspacesPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const { data: workspaces, isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: workspacesApi.list,
  })

  const createMutation = useMutation({
    mutationFn: workspacesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      setShowCreate(false)
      setName('')
      setDescription('')
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ name, description })
  }

  if (isLoading) {
    return <div>Loading workspaces...</div>
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Workspaces</h1>
          <p className="text-muted-foreground mt-1">Manage your collaborative workspaces</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="w-4 h-4 mr-2" />
          Create Workspace
        </Button>
      </div>

      {showCreate && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create New Workspace</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Workspace"
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
        {workspaces?.map((workspace: Workspace) => (
          <Link key={workspace.id} to={`/workspaces/${workspace.id}`}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Briefcase className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{workspace.name}</CardTitle>
                    {workspace.description && (
                      <CardDescription className="mt-1">{workspace.description}</CardDescription>
                    )}
                  </div>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {workspaces?.length === 0 && (
        <div className="text-center py-12">
          <Briefcase className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            No workspaces yet
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Create your first workspace to get started
          </p>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Workspace
          </Button>
        </div>
      )}
    </div>
  )
}
