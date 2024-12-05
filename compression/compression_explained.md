```markdown
# Knowledge Graph Compression Script

The `compression.py` script is designed to achieve **extreme compression** of a JSON-based knowledge graph, ensuring **no data loss** and maintaining **interpretability** for a language model (LLM).

---

## Overview

### Key Features:
1. **Load the Knowledge Graph**: Reads a JSON file containing the graph.
2. **Generate Abbreviations**: Creates unique abbreviations for every unique term.
3. **Serialize the Knowledge Graph**: Converts the graph into a compressed, custom-formatted representation.
4. **Output the Compressed Data**: Saves the compressed graph and a codebook for LLM interpretation.

---

## How It Works

### 1. **Loading the Knowledge Graph**
Reads and parses the JSON file:
```python
import json

with open("python_code_knowledge_graph.json", "r") as f:
    knowledge_graph = json.load(f)
```

### 2. **Generating Abbreviations**
Creates unique abbreviations for all terms:
```python
def generate_abbreviations(knowledge_graph):
    # Collect unique terms
    unique_terms = set()
    for node in knowledge_graph["graph"]["nodes"]:
        unique_terms.add(node["id"])
        for key, value in node.items():
            unique_terms.add(key)
            collect_terms(value, unique_terms)

    for link in knowledge_graph["graph"]["links"]:
        unique_terms.update({link["source"], link["relation"], link["target"]})

    # Assign abbreviations
    return {term: f"T{idx}" for idx, term in enumerate(sorted(unique_terms), start=1)}
```

#### **Helper Function: Recursive Term Collection**
```python
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
```

### 3. **Serializing the Knowledge Graph**
Converts the graph into a compact format:
```python
def serialize_knowledge_graph(knowledge_graph, abbreviations):
    serialized_data = ["# Compressed Knowledge Graph\n# Instructions for LLM:"]
    serialized_data.append("# - Use the codebook below to map abbreviations.")
    
    # Add Codebook
    for term, abbr in sorted(abbreviations.items(), key=lambda x: x[1]):
        serialized_data.append(f"# {abbr}:{term}")

    # Serialize Nodes
    for node in knowledge_graph["graph"]["nodes"]:
        node_id = abbreviations[node["id"]]
        attributes = [
            f"{abbreviations[k]}={abbreviate_value(v, abbreviations)}"
            for k, v in node.items() if k != "id"
        ]
        serialized_data.append(f"N|{node_id}|{' '.join(attributes)}")

    # Serialize Links
    for link in knowledge_graph["graph"]["links"]:
        serialized_data.append(f"L|{abbreviations[link['source']]}|"
                               f"{abbreviations[link['relation']]}|"
                               f"{abbreviations[link['target']]}")

    return "\n".join(serialized_data)
```

#### **Helper Function: Abbreviating Nested Values**
```python
def abbreviate_value(value, abbreviations):
    if isinstance(value, list):
        return f"[{','.join(abbreviate_value(v, abbreviations) for v in value)}]"
    elif isinstance(value, dict):
        return f"{{{','.join(f'{abbreviations[k]}:{abbreviate_value(v, abbreviations)}' for k, v in value.items())}}}"
    return abbreviations.get(str(value), str(value))
```

### 4. **Writing the Compressed Data**
Compress and save the graph:
```python
abbreviations = generate_abbreviations(knowledge_graph)
compressed_data = serialize_knowledge_graph(knowledge_graph, abbreviations)

with open("compressed_knowledge_graph.txt", "w") as f:
    f.write(compressed_data)
```

---

## Techniques Used

1. **Abbreviated Entity References**:
   - Assigns short codes (e.g., `T1`, `T2`) to terms for compression.
2. **Custom Serialization Format**:
   - Compact node and link representation:
     - **Nodes**: `N|ID|ATTR1=VAL1;ATTR2=VAL2`
     - **Links**: `L|SOURCE|RELATION|TARGET`
3. **Recursive Handling of Nested Data**:
   - Supports lists and dictionaries.
4. **Codebook Inclusion**:
   - Maps abbreviations back to terms for interpretability.
5. **LLM-Friendly Instructions**:
   - Detailed guidance for reconstructing the graph.

---

## Benefits

- **Extreme Compression**: Reduces data size significantly.
- **No Data Loss**: Preserves all graph details, including nested structures.
- **LLM Interpretability**: Includes a codebook and instructions for accurate reconstruction.

---

## Example Walkthrough

### Original Node:
```json
{
  "id": "Function: process_data",
  "type": "Function",
  "name": "process_data",
  "parameters": ["data", "config"],
  "returns": "int"
}
```

### After Compression:
- **Serialized Node**:
  ```
  N|T5|T1=T2;T3=T4;T6=[T7,T8];T9=T10
  ```
- **Codebook Entries**:
  ```
  # T1:type
  # T2:Function
  # T3:name
  # T4:process_data
  # T5:Function: process_data
  # T6:parameters
  # T7:data
  # T8:config
  # T9:returns
  # T10:int
  ```

---

## How to Use

1. **Reconstruction**:
   - Map abbreviations back using the codebook.
   - Parse and rebuild nodes and links.
2. **Analysis**:
   - Efficient storage and processing for LLMs.
   - Perform queries directly on the compressed data.

---

## Conclusion

This script compresses a JSON-based knowledge graph while maintaining data integrity and interpretability for LLMs. By using abbreviations, custom serialization, and detailed instructions, the compressed graph is efficient for storage, transmission, and analysis.

--- 

**Author**: Brandon Docusen  
**License**: MIT  
**Contact**: [brandondocusen@gmail.com]
```
