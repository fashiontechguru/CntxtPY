import sys
import json
import os
from collections import defaultdict

# Ensure a file path is provided
if len(sys.argv) != 2:
    raise ValueError("Please provide the path to 'python_code_knowledge_graph.json' as an argument.")

input_file = sys.argv[1]

# Load the knowledge graph from the JSON file
if not os.path.exists(input_file):
    raise FileNotFoundError(f"File not found: {input_file}")

with open(input_file, "r") as f:
    knowledge_graph = json.load(f)

# Function to generate abbreviations for all unique terms
def generate_abbreviations(knowledge_graph):
    unique_terms = set()
    graph = knowledge_graph["graph"]
    # Collect unique terms from nodes
    for node in graph["nodes"]:
        unique_terms.add(node["id"])
        for key, value in node.items():
            unique_terms.add(key)
            # Handle values that can be lists, dicts, or other types
            collect_terms(value, unique_terms)
    # Collect unique terms from links
    for link in graph["links"]:
        unique_terms.add(link["source"])
        unique_terms.add(link["relation"])
        unique_terms.add(link["target"])

    # Generate abbreviations
    abbreviations = {}
    idx = 1
    for term in sorted(unique_terms):
        abbreviations[term] = f"T{idx}"
        idx += 1
    return abbreviations

# Helper function to collect terms recursively
def collect_terms(value, unique_terms):
    if isinstance(value, list):
        for item in value:
            collect_terms(item, unique_terms)
    elif isinstance(value, dict):
        for k, v in value.items():
            unique_terms.add(str(k))
            collect_terms(v, unique_terms)
    else:
        unique_terms.add(str(value))

# Function to serialize the knowledge graph using abbreviations
def serialize_knowledge_graph(knowledge_graph, abbreviations):
    serialized_data = []
    graph = knowledge_graph["graph"]

    # Instructions for LLM
    instructions = (
        "# Compressed Knowledge Graph\n"
        "# Instructions for LLM:\n"
        "# - Data is compressed using abbreviations.\n"
        "# - Use the codebook to map abbreviations back to terms.\n"
        "# - Each line represents a node or link.\n"
        "# - Node lines start with 'N' and are in the format:\n"
        "#   N|ID|ATTR1=VAL1;ATTR2=VAL2;...\n"
        "# - Link lines start with 'L' and are in the format:\n"
        "#   L|SOURCE|RELATION|TARGET\n"
        "# - Attributes and values are abbreviated using the codebook.\n"
        "# - Nested structures are represented with brackets:\n"
        "#   - Lists: [VAL1,VAL2,...]\n"
        "#   - Dicts: {KEY1:VAL1,KEY2:VAL2,...}\n"
        "# Codebook:"
    )
    serialized_data.append(instructions)

    # Include the codebook
    for term, abbr in sorted(abbreviations.items(), key=lambda x: x[1]):
        serialized_data.append(f"# {abbr}:{term}")

    # Serialize nodes
    for node in graph["nodes"]:
        node_id = abbreviations[node["id"]]
        attributes = []
        for key, value in node.items():
            if key != "id":
                key_abbr = abbreviations[key]
                value_abbr = abbreviate_value(value, abbreviations)
                attributes.append(f"{key_abbr}={value_abbr}")
        attr_str = ';'.join(attributes)
        serialized_data.append(f"N|{node_id}|{attr_str}")

    # Serialize links
    for link in graph["links"]:
        source_abbr = abbreviations[link["source"]]
        relation_abbr = abbreviations[link["relation"]]
        target_abbr = abbreviations[link["target"]]
        serialized_data.append(f"L|{source_abbr}|{relation_abbr}|{target_abbr}")

    return '\n'.join(serialized_data)

# Helper function to abbreviate values recursively
def abbreviate_value(value, abbreviations):
    if isinstance(value, list):
        items = [abbreviate_value(item, abbreviations) for item in value]
        return f"[{','.join(items)}]"
    elif isinstance(value, dict):
        items = []
        for k, v in value.items():
            k_abbr = abbreviations[str(k)]
            v_abbr = abbreviate_value(v, abbreviations)
            items.append(f"{k_abbr}:{v_abbr}")
        return f"{{{','.join(items)}}}"
    else:
        return abbreviations.get(str(value), str(value))

# Generate abbreviations
abbreviations = generate_abbreviations(knowledge_graph)

# Serialize the knowledge graph
compressed_data = serialize_knowledge_graph(knowledge_graph, abbreviations)

# Ensure the "compression" directory exists
output_dir = "compression"
os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist

# Write the compressed data to the file in the "compression" directory
output_file = os.path.join(output_dir, "compressed_knowledge_graph.txt")
with open(output_file, "w") as f:
    f.write(compressed_data)
