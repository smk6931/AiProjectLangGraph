import os

# 설정
ROOT_DIR = os.getcwd()
EXPORT_DIR = os.path.join(ROOT_DIR, "code_export")
IGNORE_DIRS = {".git", "venv", "__pycache__", ".vscode", ".idea", "code_export", "tests", "tmp", "logs"}
IGNORE_FILES = {".DS_Store", "poetry.lock", "package-lock.json", "*.pyc"}
TARGET_EXTS = {".py", ".md", ".txt", ".ini", ".env.example"}

# 카테고리 매핑
CATEGORIES = {
    "Backend_App": ["app"],
    "Frontend_UI": ["ui"],
    "Docs_Config": ["docs", "scripts", "main.py", "requirements.txt", ".env.example", "README.md"]
}

def get_category(path):
    rel_path = os.path.relpath(path, ROOT_DIR)
    
    # 루트 파일 처리
    if os.path.isfile(path) and os.path.dirname(path) == ROOT_DIR:
        filename = os.path.basename(path)
        if filename in ["main.py", "requirements.txt", ".env.example", "README.md"]:
            return "Docs_Config"
        return "Misc"

    # 디렉토리 기반 매핑
    top_dir = rel_path.split(os.sep)[0]
    for cat, folders in CATEGORIES.items():
        if top_dir in folders:
            return cat
    return "Misc"

def write_file_content(f_out, file_path):
    try:
        rel_path = os.path.relpath(file_path, ROOT_DIR)
        with open(file_path, "r", encoding="utf-8") as f_in:
            content = f_in.read()
            
        f_out.write(f"\n{'='*50}\n")
        f_out.write(f"FILE_PATH: {rel_path}\n")
        f_out.write(f"{'='*50}\n\n")
        f_out.write(content)
        f_out.write("\n\n")
        print(f"✅ Included: {rel_path}")
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")

def main():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        
    files_by_cat = {cat: [] for cat in CATEGORIES.keys()}
    files_by_cat["Misc"] = []

    # 파일 수집
    for root, dirs, files in os.walk(ROOT_DIR):
        # 무시할 폴더 제거
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in TARGET_EXTS and file not in ["requirements.txt", ".env.example", "Dockerfile"]:
                continue
                
            full_path = os.path.join(root, file)
            cat = get_category(full_path)
            files_by_cat[cat].append(full_path)

    # 파일 쓰기
    for cat, paths in files_by_cat.items():
        if not paths: continue
        
        out_path = os.path.join(EXPORT_DIR, f"PROJECT_SOURCE_{cat}.txt")
        with open(out_path, "w", encoding="utf-8") as f_out:
            f_out.write(f"Project Code Export - Category: {cat}\n")
            f_out.write(f"Generated for Gemini Canvas Analysis\n\n")
            
            for path in sorted(paths): # 정렬해서 일관성 유지
                write_file_content(f_out, path)
                
    print(f"\n✨ Export Completed to: {EXPORT_DIR}")

if __name__ == "__main__":
    main()
