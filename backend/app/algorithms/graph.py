"""
Graph algorithms for task dependency management.

This module implements critical algorithms for managing task dependencies:
1. Cycle detection using DFS to prevent circular dependencies
2. Topological sorting using Kahn's algorithm
3. Critical path calculation for project scheduling

Time Complexity:
- has_cycle: O(V + E) where V is number of tasks, E is number of dependencies
- topological_sort: O(V + E) using Kahn's algorithm
- critical_path: O(V + E) for DAG traversal

Space Complexity:
- All algorithms: O(V + E) for graph representation and auxiliary data structures
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque


class TaskGraph:
    """Directed graph representation of task dependencies"""
    
    def __init__(self):
        self.graph: Dict[str, List[str]] = defaultdict(list)  # adjacency list
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)  # for critical path
        self.task_durations: Dict[str, int] = {}  # estimated hours for each task
    
    def add_task(self, task_id: str, duration: int = 0):
        """Add a task node to the graph"""
        if task_id not in self.graph:
            self.graph[task_id] = []
        if task_id not in self.reverse_graph:
            self.reverse_graph[task_id] = []
        self.task_durations[task_id] = duration
    
    def add_dependency(self, task_id: str, depends_on_id: str):
        """
        Add a dependency edge: task_id depends on depends_on_id
        This means depends_on_id must be completed before task_id
        """
        self.graph[depends_on_id].append(task_id)
        self.reverse_graph[task_id].append(depends_on_id)
    
    def has_cycle(self) -> bool:
        """
        Detect if the graph contains a cycle using DFS.
        
        Uses three-color marking:
        - White (0): unvisited
        - Gray (1): visiting (in current DFS path)
        - Black (2): visited (finished)
        
        A back edge to a gray node indicates a cycle.
        
        Time Complexity: O(V + E)
        Space Complexity: O(V)
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.graph}
        
        def dfs(node: str) -> bool:
            """Returns True if cycle detected"""
            color[node] = GRAY
            
            for neighbor in self.graph[node]:
                if color.get(neighbor, WHITE) == GRAY:
                    # Back edge found - cycle detected
                    return True
                if color.get(neighbor, WHITE) == WHITE:
                    if dfs(neighbor):
                        return True
            
            color[node] = BLACK
            return False
        
        # Check all components (graph may be disconnected)
        for node in self.graph:
            if color[node] == WHITE:
                if dfs(node):
                    return True
        
        return False
    
    def topological_sort(self) -> Optional[List[str]]:
        """
        Perform topological sort using Kahn's algorithm.
        
        Returns list of task IDs in valid execution order, or None if cycle exists.
        
        Algorithm:
        1. Calculate in-degree for all nodes
        2. Add all nodes with in-degree 0 to queue
        3. Process queue: remove node, decrease in-degree of neighbors
        4. If all nodes processed, return order; otherwise cycle exists
        
        Time Complexity: O(V + E)
        Space Complexity: O(V)
        """
        # Calculate in-degree for each node
        in_degree = {node: 0 for node in self.graph}
        for node in self.graph:
            for neighbor in self.graph[node]:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
        
        # Initialize queue with nodes having no dependencies
        queue = deque([node for node in self.graph if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # Reduce in-degree of neighbors
            for neighbor in self.graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If all nodes processed, valid topological order exists
        if len(result) == len(self.graph):
            return result
        else:
            # Cycle detected
            return None
    
    def critical_path(self) -> Tuple[List[str], int]:
        """
        Calculate the critical path - longest path through the DAG.
        
        The critical path represents the minimum time to complete the project
        and identifies tasks that cannot be delayed without delaying the project.
        
        Returns: (critical_path_tasks, total_duration)
        
        Algorithm:
        1. Perform topological sort
        2. Calculate earliest start time for each task
        3. Find task with maximum finish time
        4. Backtrack to find critical path
        
        Time Complexity: O(V + E)
        Space Complexity: O(V)
        """
        topo_order = self.topological_sort()
        if not topo_order:
            # Cycle exists, cannot calculate critical path
            return [], 0
        
        # Calculate earliest start time for each task
        earliest_start = {node: 0 for node in self.graph}
        predecessor = {node: None for node in self.graph}
        
        for node in topo_order:
            duration = self.task_durations.get(node, 0)
            finish_time = earliest_start[node] + duration
            
            # Update successors
            for successor in self.graph[node]:
                if finish_time > earliest_start[successor]:
                    earliest_start[successor] = finish_time
                    predecessor[successor] = node
        
        # Find the task with maximum finish time
        if not earliest_start:
            return [], 0
        
        end_node = max(earliest_start.items(), key=lambda x: x[1] + self.task_durations.get(x[0], 0))
        max_duration = end_node[1] + self.task_durations.get(end_node[0], 0)
        
        # Backtrack to find critical path
        critical_path = []
        current = end_node[0]
        
        while current is not None:
            critical_path.append(current)
            current = predecessor[current]
        
        critical_path.reverse()
        
        return critical_path, max_duration
    
    def get_blocked_tasks(self) -> Dict[str, List[str]]:
        """
        Get all tasks that are blocked by incomplete dependencies.
        
        Returns a dictionary mapping each task to its list of blocking tasks
        (tasks it depends on that must be completed first).
        """
        blocked = {}
        for task_id in self.graph:
            dependencies = self.reverse_graph.get(task_id, [])
            if dependencies:
                blocked[task_id] = dependencies
        return blocked


def build_task_graph(tasks: List[Dict], dependencies: List[Dict]) -> TaskGraph:
    """
    Build a TaskGraph from database records.
    
    Args:
        tasks: List of task dictionaries with 'id' and 'estimated_hours'
        dependencies: List of dependency dictionaries with 'task_id' and 'depends_on_id'
    
    Returns:
        Constructed TaskGraph instance
    """
    graph = TaskGraph()
    
    # Add all tasks
    for task in tasks:
        task_id = task['id']
        duration = task.get('estimated_hours', 0) or 0
        graph.add_task(task_id, duration)
    
    # Add all dependencies
    for dep in dependencies:
        graph.add_dependency(dep['task_id'], dep['depends_on_id'])
    
    return graph
