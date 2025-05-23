#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ball-Larus path profiling implementation for the Chiron Framework.
"""

from operator import is_
from os import path
import sys
from tabnanny import check
import networkx as nx
from networkx import MultiDiGraph
from networkx import efficiency
from ChironAST import ChironAST
from irhandler import IRHandler
from interpreter import ConcreteInterpreter
from BallLarus.bl_interpreter import BallLarusInterpreter
import turtle
from networkx.drawing.nx_agraph import to_agraph
import json

class BallLarusProfiler:
    """
    Implements Ball-Larus path profiling algorithm.
    """
    
    def __init__(self, irHandler, args):
        """
        Initialize the Ball-Larus profiler.
        """
        self.irHandler = irHandler
        self.ir = irHandler.ir
        self.cfg = irHandler.cfg
        self.original_ir = None  # To store the original IR before instrumentation
        self.back_edges = []  # List of back edges in the CFG
        self.args = args

    def run_profiling(self):
        """
        Run the Ball-Larus path profiling algorithm.
        
        This involves:
        1. Saving the original IR
        2. Identifying paths in the CFG
        3. Computing edge weights
        4. Instrumenting the IR
        5. Running the instrumented program
        6. Reporting the results
        """
        # Save the original IR
        self.original_ir = self.ir.copy()
        
        # Identify paths and compute edge weights
        self.compute_edge_weights()
        
        # Instrument the IR
        self.instrument_ir()

    def execute(self, predictor_hashMap = {}, flag = False, is_training = False):
        """
        Execute the instrumented program.
        """
        inptr = BallLarusInterpreter(self.irHandler, self.args, predictor_hashMap, flag, is_training)
        terminated = False
        inptr.initProgramContext(self.args.params)
        while True:
            terminated = inptr.interpret()
            if terminated:
                break
        print("Program Ended.")
        print()
        print("Press ESCAPE to exit")

        turtle.listen()
        if  flag == False:
            turtle.onkeypress(stopTurtle, "Escape")
            turtle.mainloop()

    def compute_edge_weights(self):
        """
        Compute edge weights using the Ball-Larus algorithm.
        
        The algorithm works as follows:
        1. Make the CFG acyclic by removing back edges
        2. Assign a value NumPaths(v) to each node v, which is the number of paths from v to the exit node
        3. Assign weights to edges such that the sum of weights along any path gives a unique path number
        """
        # Create an acyclic version of the CFG
        self.acyclic_cfg = self.create_acyclic_cfg()
        
        # Compute NumPaths for each node using a topological sort
        # NumPaths(exit) = 1
        # NumPaths(v) = sum(NumPaths(w)) for all edges v->w
        num_paths = {self.exit_node: 1}

        # Get nodes in reverse topological order (from exit to entry)
        try:
            for node in reversed(list(nx.topological_sort(self.acyclic_cfg))):
                if node not in num_paths:
                    num_paths[node] = 0
                
                for edge in self.acyclic_cfg.out_edges(node):
                    successor = edge[1]
                    if successor in num_paths:
                        num_paths[node] += num_paths[successor]
        except nx.NetworkXUnfeasible:
            print("Error: Could not perform topological sort on the CFG")
            return
        
        # Assign weights to edges
        # For each node v (except exit), in topological order:
        #   val = 0
        #   For each edge v->w:
        #     weight(v->w) = val
        #     val += NumPaths(w)
        for node in reversed(list(nx.topological_sort(self.acyclic_cfg))):
            if node == self.exit_node:
                continue
            
            val = 0
            for edge in self.acyclic_cfg.out_edges(node, data=True):
                successor = edge[1]
                edge[2]['weight'] = val
                edge[2]['chord_edge'] = False
                if successor in num_paths:
                    val += num_paths[successor]

            assert val == num_paths[node]

        # DEBUG: Print the acyclic CFG with edge weights
        # print("Edge weights computed successfully")
        # for node in self.acyclic_cfg.nodes():
        #     for edge in self.acyclic_cfg.out_edges(node, data=True):
        #         print(f"{node.name} -> {edge[1].name}: {edge[2]['weight']}")

        self.efficient_event_counting()
        # Now we will use the efficient event counting algorithm to compute the edge weights

    def efficient_event_counting(self):
        # Create a copy of the acyclic CFG as a MultiDiGraph
        mst_graph = nx.MultiDiGraph(self.acyclic_cfg)
        
        # Add an edge from exit to entry with very high weight (practically infinity)
        inf = 1000000000
        mst_graph.add_edge(self.exit_node, self.entry_node, weight=inf) #inf = 1e9
        
        # Implement Kruskal's algorithm for maximum spanning tree
        # 1. Get all edges with their weights and sort by weight in descending order
        edges = []
        for u, v, data in mst_graph.edges(data=True):
            weight = data.get('weight', 0)
            edges.append((u, v, weight, data))
        
        # Sort edges by weight in descending order (for maximum spanning tree)
        edges.sort(key=lambda x: x[2], reverse=True)
        
        # Initialize a disjoint-set data structure for cycle detection
        # We'll use a simple dictionary for this
        parent = {node: node for node in mst_graph.nodes()}
        
        def find(node):
            # Find the root/representative of the set containing node
            if parent[node] != node:
                parent[node] = find(parent[node])  # Path compression
            return parent[node]
        
        def union(node1, node2):
            # Merge the sets containing node1 and node2
            root1 = find(node1)
            root2 = find(node2)
            if root1 != root2:
                parent[root2] = root1
        
        # Build the MST
        mst_edges = []
        for u, v, weight, data in edges:
            # Skip adding this edge if it would create a cycle
            if find(u) != find(v):
                mst_edges.append((u, v, data))
                union(u, v)
        
        # Mark all edges as chord_edge=True by default
        for u, v, data in mst_graph.edges(data=True):
            data['chord_edge'] = True
        
        for u, v, data in mst_edges:
            for edge in mst_graph.out_edges(u, data=True):
                if edge[1] == v and edge[2] == data:
                    edge[2]['chord_edge'] = False

        # print("---------------------------------")
        # print("Chord edges:")
        # for u,v,data in mst_graph.edges(data=True):
        #     if data['chord_edge']:
        #         print(f"{u.name} -> {v.name}: {data['weight']}")

        # mst_tree will be an undirected graph
        mst_tree = nx.DiGraph()
        for u,v,data in mst_graph.edges(data=True):
            if(data['chord_edge'] == False):
                weight = data['weight']
                if(u == self.exit_node and v == self.entry_node):
                    # print("Dummy edge from exit to entry")
                    weight = 0
                # mst_tree.add_edge(u,v,weight)
                mst_tree.add_edge(u,v,weight=weight)
                mst_tree.add_edge(v,u,weight= -weight)

        for u, v, data in mst_graph.edges(data=True):
            if data['chord_edge']:
                # Use DFS to calculate the path weight sum from u to v in the MST
                path_weight_sum = 0
                vis = {}
                def dfs_path(node, target, weight_sum):
                    """
                    Recursive DFS to find a path and its weight sum from node to target.
                    Returns True if a path is found, False otherwise.
                    """
                    if node in vis:
                        return False
                    vis[node] = True
                    nonlocal path_weight_sum
                    if node == target:
                        path_weight_sum = weight_sum
                        return True
                    
                    # print(len(mst_tree.out_edges(node)))
                    for edge in mst_tree.out_edges(node, data=True):
                        successor = edge[1]
                        # print(f"  {node.name} -> {successor.name}: {edge[2]['weight']}")
                        if dfs_path(successor, target, weight_sum + edge[2]['weight']):
                            return True
                            
                    return False
                
                # Start DFS from u to find a path to v
                # print(f"Finding path from {u.name} to {v.name}")
                path_found = dfs_path(v, u, 0)
                if path_found == False:
                    assert False
                    path_found = dfs_path(u, v, 0)
                assert path_found == True

                data['weight2'] = data['weight']
                data['weight'] += path_weight_sum
                # print(f"{u.name} ----> {v.name}: {data['weight']}")
        
        for u, v, data in mst_graph.edges(data=True):
            if data['chord_edge'] == False:
                data['weight2'] = data['weight']
                data['weight'] = 0

        # Remove the dummy edge from exit to entry
        mst_graph.remove_edge(self.exit_node, self.entry_node)
        # print("---------------------- New weights ----------------------")
        # for u,v,data in mst_graph.edges(data=True):
        #     print(f"{u.name} -> {v.name}: {data['weight']}")
        
        self.acyclic_cfg = mst_graph
    
    def instrument_ir(self):
        """
        Instrument the IR to track path execution.

        This involves:
        1. Adding a path register variable.
        2. For each "flow_edge" and "Cond_True":
             - Locate the last IR index of the source basic block and insert an update
               instruction immediately after.
        3. For each "Cond_False":
             - Append at the end of the IR two instructions:
                 a) an update to the path register,
                 b) a goto command that jumps to the target basic block's first instruction.
        4. The instrumentation for the back edges were handled separately.
        5. After adding instructions, the offsets were updated simultaneously.
        """
        
        # DEBUG: Print the original IR
        # print("Original IR:")
        # for instr, idx in self.ir:
        #     print(f"instr: {instr}, target: {idx}")
        # print("--------------------------------")

        # Save original IR copy
        if self.original_ir is None:
            self.original_ir = self.ir.copy()

        # Create a path register variable
        path_register_var = ChironAST.Var(":blPathRegister")
        
        # Insert an initialization instruction at the beginning
        init_path_register = ChironAST.AssignmentCommand(
            path_register_var, 
            ChironAST.Num(0)
        )
        
        # Build mapping from each basic block to its first and last IR indices
        bb_last_index = {}
        bb_first_index = {}
        for bb in self.cfg.nodes():
            if bb.instrlist:
                bb_first_index[bb] = bb.instrlist[0][1]
                bb_last_index[bb] = bb.instrlist[-1][1]

        # Helper function to update bb indices and IR targets after an insertion.
        def update_offsets(insertion_index, delta=1):
            # Update basic block first and last indices
            for bb in bb_first_index:
                if bb_first_index[bb] >= insertion_index:
                    bb_first_index[bb] += delta
                if bb_last_index[bb] >= insertion_index:
                    bb_last_index[bb] += delta
            # Update each IR instruction's jump offset
            for idx, (instr, tgt) in enumerate(new_ir):
                jump_target = idx + tgt
                if(idx == insertion_index - 1):
                    if isinstance(instr, ChironAST.ConditionCommand) and jump_target >= insertion_index:
                        new_tgt = tgt + delta
                        new_ir[idx] = (instr, new_tgt)
                    continue
                if(idx == insertion_index):
                    continue
                # For instructions before the insertion:
                if idx < insertion_index and jump_target >= insertion_index:
                    new_tgt = tgt + delta
                    new_ir[idx] = (instr, new_tgt)
                # For instructions at/after the insertion:
                elif idx >= insertion_index and jump_target <= insertion_index:
                    new_tgt = tgt - delta
                    new_ir[idx] = (instr, new_tgt)
        
        # Work on a copy of the IR list for insertions
        new_ir = self.irHandler.ir.copy()
        new_ir.insert(0, (init_path_register, 1))
        update_offsets(0)

        # Iterate over CFG edges
        for source, target, attrs in self.cfg.nxgraph.edges(data=True):

            if (source, target) in self.back_edges:
                continue

            edge_label = attrs.get('label')
            weight = 0
            for edge in self.acyclic_cfg.out_edges(source, data=True):
                if edge[1] == target and edge[2].get('new_edge') is None:
                    weight = edge[2]['weight']
                    break
            # if weight == 0:
            #     continue
            # Create the update instruction: path_register = path_register + weight
            update_instr = ChironAST.AssignmentCommand(
                path_register_var,
                ChironAST.Sum(path_register_var, ChironAST.Num(weight))
            )
            
            if edge_label in ('flow_edge', 'Cond_True'):
                last_idx = bb_last_index.get(source)
                if last_idx is not None:
                    insertion_index = last_idx + 1
                    new_ir.insert(insertion_index, (update_instr, 1))
                    # After each insertion update indices and offsets.
                    update_offsets(insertion_index)

            elif edge_label == 'Cond_False':
                assert  target.name != "END"

            if(target.name == "END"):
                jump_instr = ChironAST.ConditionCommand(ChironAST.BoolFalse())
                new_ir.append((jump_instr, 1))
                update_offsets(len(new_ir)-1)
        
        # Iterate over CFG edges 2nd time to handle Cond_False edges
        for source, target, attrs in self.cfg.nxgraph.edges(data=True):
            if (source, target) in self.back_edges:

                # Part 1
                weight = 0
                check_flag = 0
                for edge in self.acyclic_cfg.out_edges(source, data=True):
                    if edge[1] == self.exit_node and edge[2].get('new_edge') is True:
                        check_flag = 1
                        weight = edge[2]['weight']
                        break
                assert check_flag == 1
                update_instr = ChironAST.AssignmentCommand(
                    path_register_var,
                    ChironAST.Sum(path_register_var, ChironAST.Num(weight))
                )
                insertion_index = len(new_ir) 
                new_ir.append((update_instr, 1))
                update_offsets(insertion_index)
                source_end = bb_last_index.get(source, 0)
                instr, old_offset = new_ir[source_end]
                new_offset = len(new_ir) - source_end - 1
                new_ir[source_end] = (instr, new_offset)

                inc_instr = ChironAST.IncrementCommand(path_register_var)
                new_ir.append((inc_instr, 1))
                update_offsets(len(new_ir)-1)

                # Part 2
                check_flag = 0
                for edge in self.acyclic_cfg.out_edges(self.entry_node, data=True):
                    if edge[1] == target and edge[2].get('new_edge') is True:
                        weight = edge[2]['weight']
                        check_flag = 1
                        break
                
                assert check_flag == 1
                update_instr = ChironAST.AssignmentCommand(
                    path_register_var,
                    ChironAST.Num(weight)
                )
                insertion_index = len(new_ir)
                new_ir.append((update_instr, 1))
                update_offsets(insertion_index)
                jump_instr = ChironAST.ConditionCommand(ChironAST.BoolFalse())
                target_first = bb_first_index.get(target, 0)
                val = target_first - len(new_ir)
                new_ir.append((jump_instr, val))
                update_offsets(len(new_ir)-1)  

                continue
            
            
            edge_label = attrs.get('label')
            weight = 0
            for edge in self.acyclic_cfg.out_edges(source, data=True):
                if edge[1] == target and edge[2].get('new_edge') is None:
                    weight = edge[2]['weight']
                    break

            update_instr = ChironAST.AssignmentCommand(
                path_register_var,
                ChironAST.Sum(path_register_var, ChironAST.Num(weight))
            )
            
            if edge_label == 'Cond_False':
                insertion_index = len(new_ir) 
                new_ir.append((update_instr, 1))
                update_offsets(insertion_index)
                source_end = bb_last_index.get(source, 0)
                target_first = bb_first_index.get(target, 0)
                instr, old_offset = new_ir[source_end]
                new_offset = len(new_ir) - source_end - 1
                new_ir[source_end] = (instr, new_offset)
                jump_instr = ChironAST.ConditionCommand(ChironAST.BoolFalse())
                val = target_first - len(new_ir)
                new_ir.append((jump_instr, val))
                update_offsets(len(new_ir)-1)

        # Dump the HashMap to a file
        inc_instr = ChironAST.IncrementCommand(path_register_var)
        new_ir.append((inc_instr, 1))
        dump_instr = ChironAST.DumpCommand()
        new_ir.append((dump_instr, 1))

        # Replace IR with instrumented version
        self.irHandler.ir = new_ir
        
        print("--------------------------------")
        print("IR:")
        for instr, idx in self.irHandler.ir:
            print(f"instr: {instr}, target: {idx}")
        print("--------------------------------")
        print("IR instrumented successfully for Ball-Larus path profiling")

    def regenerate_path(self, path_number):
        """
        Regenerate the path from the path number.
        
        This method uses the edge weights to reconstruct the path taken
        in the CFG to reach the given path number.
        
        Args:
            path_number: The path number to regenerate
        
        Returns:
            A list of basic block names representing the path
        """

        path = []
        current_node = self.entry_node
        while current_node is not None and current_node.name != "END":
            path.append(current_node.name)
            max_weight = -1
            next_node = None
            new_edge = False
            for edge in self.acyclic_cfg.out_edges(current_node, data=True):
                weight = edge[2].get('weight2', 0)
                if weight > max_weight and path_number >= weight:
                    max_weight = weight
                    next_node = edge[1]
                    new_edge = edge[2].get('new_edge', False)

            if new_edge and path[-1] == "START":
                path.pop()
            path_number -= max_weight
            current_node = next_node
        
        if new_edge == False:
            path.append("END")

        return path
    
    def report_results(self):
        """
        Report the results of path profiling.
        
        This method should be called after the instrumented program has been executed.
        """
        # Open hash_dump.txt and read the hash map contents
        # example contents ->
        #  4: 3
        # 15: 12
        # for each key: value pair, we will replace the key with the actual path in the CFG by implementing the path regeneration algorithm
        # then write back the path: value pair to hash_dump.txt
        list_of_paths = []
        with open("hash_dump.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                key, value = line.split(":")
                path = self.regenerate_path(int(key))
                #store the path: value pair in the hash_dump.txt file
                list_of_paths.append((path, value))
        with open("path_profile_data.txt", "w") as f:
            for path, value in list_of_paths:
                f.write(f"{path}: {value}")
    
    def identify_back_edges(self):
        """
        Identify back edges in the CFG.
        
        Back edges are edges that point from a node to one of its ancestors
        in a depth-first traversal of the graph. These edges typically
        represent loops in the program.
        
        Returns:
            A list of tuples (source, target) representing back edges
        """
        # Get the NetworkX graph from the CFG
        G = self.cfg.nxgraph
        
        # Initialize variables for DFS
        visited = set()
        dfs_stack = []  # Stack to track the current DFS path
        back_edges = []
        
        # Define a recursive DFS function
        def dfs(node):
            visited.add(node)
            dfs_stack.append(node)
            
            for successor in self.cfg.successors(node):
                if successor not in visited:
                    # Recursive DFS call
                    dfs(successor)
                elif successor in dfs_stack:
                    # Found a back edge
                    back_edges.append((node, successor))
            
            dfs_stack.pop()
        
        # Find the entry node (usually named "START")
        entry_node = None
        for node in self.cfg.nodes():
            if node.name == "START":
                entry_node = node
                break
        
        if entry_node is None:
            print("Warning: Could not find entry node in CFG")
            return []
        
        # Start DFS from the entry node
        dfs(entry_node)
        self.entry_node = entry_node

        # print(f"Identified {len(back_edges)} back edges in the CFG")
        # for source, target in back_edges:
        #     print(f"  {source.name} -> {target.name}")
        return back_edges

    def create_acyclic_cfg(self):
        """
        Create an acyclic version of the CFG by removing back edges.
        
        Returns:
            A new NetworkX DiGraph that is acyclic
        """
        # Get the original graph
        G = nx.MultiDiGraph(self.cfg.nxgraph)

        # Identify back edges
        self.back_edges = self.identify_back_edges()
        
        exit_node = None
        for node in self.cfg.nodes():
            if node.name == "END":
                exit_node = node
                break

        self.exit_node = exit_node

        # Remove back edges from the graph
        for source, target in self.back_edges:
            if G.has_edge(source, target):
                G.remove_edge(source, target)
                G.add_edge(self.entry_node, target, new_edge=True)
                G.add_edge(source, self.exit_node, new_edge=True)
        
        # Verify that the graph is acyclic
        if nx.is_directed_acyclic_graph(G):
            print("Successfully created acyclic CFG")
        else:
            print("Warning: CFG is still cyclic after removing back edges")
        
        self.dumpCFG2(G, "acyclic_cfg.dot")
        return G
    
    def dumpCFG2(self,G,filename="out"):
        A = to_agraph(G)
        A.layout('dot')
        A.draw(filename + ".png")

def stopTurtle():
    turtle.bye()

def run_ball_larus_profiling(irHandler, args):
    """
    Main function to run Ball-Larus path profiling.
    
    If args.ballLarus_op is a filename, read one JSON dict per line,
    set args.params, and run profiling for each. Otherwise do one run.
    """
    if irHandler.cfg is None:
        print("Error: Control Flow Graph is required for Ball-Larus path profiling.")
        return

    # Always start with an empty hash_dump.txt
    with open("hash_dump.txt", "w") as dumpf:
        # open in write mode to create/clear the file
        pass
    with open("predictor_accuracy.txt", "w") as dumpf:
        # open in write mode to create/clear the file
        pass
    with open("predictions_pc.txt", "w") as dumpf:
        # open in write mode to create/clear the file
        pass

    # if -bl_op was passed, args.ballLarus_op holds the inputs‐file path
    profiler = BallLarusProfiler(irHandler, args)
    profiler.run_profiling()

    predictor_hashMap = {}
    if args.ballLarus_op:
        with open(args.ballLarus_op, 'r') as f:
            lines = [ln.strip() for ln in f
                     if ln.strip() and not ln.strip().startswith("#")]
        
        num_inputs = len(lines)
        #print(f"Found {num_inputs} inputs in {args.ballLarus_op}")
        # training_input is floor of num_inputs*0.8
        training_input = int(num_inputs * 0.8)

        # Now iterate over those lines
        for idx, ln in enumerate(lines):
            try:
                params = json.loads(ln)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {ln}\n  {e}")
                continue

            args.params = params
            turtle.clearscreen()
            turtle.reset()

            # first 80% are training runs
            is_train = (idx < training_input)
            print(f"\n=== Run #{idx+1}/{num_inputs} "
                  f"{'(training)' if is_train else '(testing)'} with params {params} ===")
            profiler.execute(predictor_hashMap,flag=True, is_training=is_train)
        
        profiler.report_results()
        turtle.onkeypress(stopTurtle, "Escape")
        turtle.mainloop()
    else:
        # single‐input mode
        profiler.execute()
        profiler.report_results()