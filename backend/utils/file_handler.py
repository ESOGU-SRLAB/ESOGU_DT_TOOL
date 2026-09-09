import os
import xml.etree.ElementTree as ET
import logging
from utils.XmlParser import parse_uml_xml_to_json
import json
from utils.UmlToXml import convert_uml_to_xml

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self):
        pass

    async def save_files(self, files):
        file_paths = []
        for file in files:
            storage_name = os.path.basename(getattr(file, "storage_name", file.filename))
            path = os.path.join(UPLOAD_DIR, storage_name)
            with open(path, "wb") as f:
                f.write(await file.read())
            file_paths.append(path)
        return file_paths

    def read_file(self, path):
        try:
            if path.lower().endswith('.uml'):
                # .uml dosyasını XML string'e çevir ve döndür
                xml_content = convert_uml_to_xml(path)
                logger.info("Converted UML input to XML (%d characters)", len(xml_content))
                return xml_content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if path.lower().endswith('.xml'):
                    # XML'i JSON'a çevir
                    json_obj = parse_uml_xml_to_json(content)
                    json_str = json.dumps(json_obj, ensure_ascii=False, indent=2)
                    logger.info("Converted XML input to JSON (%d characters)", len(json_str))
                    return json_str
                else:
                    logger.info("Read input file %s (%d characters)", os.path.basename(path), len(content))
                return content
        except UnicodeDecodeError:
            # Farklı encoding ile tekrar dene
            with open(path, 'r', encoding='ISO-8859-9') as f:
                content = f.read()
                if path.lower().endswith('.xml'):
                    json_obj = parse_uml_xml_to_json(content)
                    json_str = json.dumps(json_obj, ensure_ascii=False, indent=2)
                    logger.info("Converted ISO-8859-9 XML input to JSON (%d characters)", len(json_str))
                    return json_str
                else:
                    logger.info("Read ISO-8859-9 input file %s (%d characters)", os.path.basename(path), len(content))
                return content
        except Exception as e:
            print(f"[FileHandler] Dosya okunamadı: {str(e)}")
            return f"Dosya okunamadı: {str(e)}"

    def cleanup_files(self, file_paths):
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)

    def extract_file_metadata(self, path):
        """
        Extract metadata and key information from file for prompt generation
        """
        try:
            file_name = os.path.basename(path)
            file_ext = os.path.splitext(file_name)[1].lower()
            file_size = os.path.getsize(path)
            
            metadata = {
                "name": file_name,
                "extension": file_ext,
                "size": file_size,
                "type": self._determine_file_type(file_ext),
                "encoding": "utf-8"
            }
            
            return metadata
        except Exception as e:
            return {"name": os.path.basename(path), "error": str(e)}

    def _determine_file_type(self, extension):
        """
        Determine file type category for better processing
        """
        code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs']
        web_extensions = ['.html', '.css', '.jsx', '.tsx', '.vue']
        data_extensions = ['.json', '.xml', '.yaml', '.yml', '.csv']
        doc_extensions = ['.txt', '.md', '.rst', '.doc', '.docx']
        
        if extension in code_extensions:
            return "code"
        elif extension in web_extensions:
            return "web"
        elif extension in data_extensions:
            return "data"
        elif extension in doc_extensions:
            return "documentation"
        elif extension == '.uml':
            return "diagram"
        else:
            return "generic"

    def analyze_code_structure(self, content, file_type):
        """
        Analyze code structure for prompt generation context
        """
        if file_type != "code":
            return {}
        
        lines = content.split('\n')
        structure = {
            "functions": [],
            "classes": [],
            "imports": [],
            "comments": [],
            "line_count": len(lines)
        }
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Function detection
            if any(pattern in line_stripped for pattern in ['def ', 'function ', 'func ']):
                structure["functions"].append({"line": line_num, "content": line_stripped})
            
            # Class detection
            elif 'class ' in line_stripped:
                structure["classes"].append({"line": line_num, "content": line_stripped})
            
            # Import detection
            elif any(pattern in line_stripped for pattern in ['import ', 'from ', '#include', 'using ']):
                structure["imports"].append({"line": line_num, "content": line_stripped})
            
            # Comment detection
            elif line_stripped.startswith(('#', '//', '/*', '"""', "'''")):
                structure["comments"].append({"line": line_num, "content": line_stripped})
        
        return structure
