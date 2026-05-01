import networkx as nx
import matplotlib.pyplot as plt
from constraint import Problem

plots = ["p1", "p2", "p3", "p4", "p5"]
neighbors = [("p1", "p2"), ("p1", "p3"), ("p2", "p3"), ("p4", "p5")]


G = nx.Graph()
G.add_nodes_from(plots)
G.add_edges_from(neighbors)

pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color="#7D6B34FF", node_size=1200)
plt.show()

crops = ["wheat", "potato", "carrot", "corn", "barley"]
previous_crop = {"p1": "wheat", "p2": "potato", "p3": "carrot", "p4": "corn", "p5": "barley"}

problem = Problem()

for node in G.nodes():
    problem.addVariable(node, crops)


for node in G.nodes():
    for n in G.neighbors(node):
        problem.addConstraint(lambda a, b: a != b, (node, n))


for p in G.nodes():
    prev = previous_crop[p]
    problem.addConstraint(lambda c, prev=prev: c != prev, (p,))

solution = problem.getSolution()
print(solution)

color_map = {
    "wheat": "#a7923e",
    "potato": "#765b00ff",
    "carrot": "#ff9501",
    "barley": "#27ae60",
    "corn": "#ffee00"
}

colors = [color_map[solution[node]] for node in G.nodes()]
nx.draw(G, pos, node_color=colors, with_labels=True, node_size=1200)
plt.show()






