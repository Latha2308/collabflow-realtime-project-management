import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '@/services/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, CheckCircle2, Clock, AlertCircle } from 'lucide-react'

export default function AnalyticsPage() {
  const { projectId } = useParams<{ projectId: string }>()

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', projectId],
    queryFn: () => analyticsApi.getProjectOverview(projectId!),
    enabled: !!projectId,
  })

  const { data: graphAnalysis } = useQuery({
    queryKey: ['graph-analysis', projectId],
    queryFn: () => analyticsApi.getGraphAnalysis(projectId!),
    enabled: !!projectId,
  })

  if (isLoading) {
    return <div>Loading analytics...</div>
  }

  if (!analytics) {
    return <div>No data available</div>
  }

  const statusData = Object.entries(analytics.tasks_by_status || {}).map(([key, value]) => ({
    name: key.replace('_', ' '),
    value: value as number
  }))

  const priorityData = Object.entries(analytics.tasks_by_priority || {}).map(([key, value]) => ({
    name: key,
    value: value as number
  }))

  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Project Analytics</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.total_tasks}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.completed_tasks}</div>
            <p className="text-xs text-muted-foreground">
              {analytics.completion_rate.toFixed(1)}% completion rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.in_progress_tasks}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.overdue_tasks}</div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Tasks by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tasks by Priority</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priorityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Graph Analysis */}
      {graphAnalysis && (
        <Card>
          <CardHeader>
            <CardTitle>Dependency Graph Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium mb-2">Critical Path</h3>
                <p className="text-muted-foreground">
                  Duration: {graphAnalysis.critical_path_duration} hours
                </p>
                <p className="text-sm text-muted-foreground">
                  {graphAnalysis.critical_path.length} tasks on critical path
                </p>
              </div>

              {graphAnalysis.has_cycle && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-md">
                  <p className="text-red-600 dark:text-red-400 font-medium">
                    Warning: Circular dependencies detected!
                  </p>
                </div>
              )}

              {Object.keys(graphAnalysis.blocked_tasks || {}).length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Blocked Tasks</h3>
                  <p className="text-sm text-muted-foreground">
                    {Object.keys(graphAnalysis.blocked_tasks).length} tasks have dependencies
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
