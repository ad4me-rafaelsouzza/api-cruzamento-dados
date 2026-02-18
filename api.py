#!/usr/bin/env python3
"""
API de Cruzamento de Dados V4 - INTELIGENTE E RÁPIDA
Versão com queries otimizadas, cache e cruzamento correto entre bancos
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import sqlite3
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
import logging
import time

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

GDRIVE_MOUNT = os.path.expanduser("~/gdrive_mount")

DATABASES = {
    "contatos": {
        "file": os.path.join(GDRIVE_MOUNT, "SRS_CONTATOS.db"),
        "table": "SRS_CONTATOS",
        "key_field": "CONTATOS_ID",
        "description": "Dados cadastrais de contatos",
    },
    "poder_aquisitivo": {
        "file": os.path.join(GDRIVE_MOUNT, "SRS_TB_PODER_AQUISITIVO.db"),
        "table": "SRS_TB_PODER_AQUISITIVO",
        "key_field": "CONTATOS_ID",
        "description": "Dados de poder aquisitivo e renda",
    },
    "historico_telefones": {
        "file": os.path.join(GDRIVE_MOUNT, "SRS_HISTORICO_TELEFONES.db"),
        "table": "SRS_HISTORICO_TELEFONES",
        "key_field": "CONTATOS_ID",
        "description": "Histórico de telefones e contatos",
    },
    "irpf": {
        "file": os.path.join(GDRIVE_MOUNT, "SRS_TB_IRPF.db"),
        "table": "SRS_TB_IRPF",
        "key_field": "DocNumber",
        "description": "Dados de IRPF",
    },
}

# ============================================================================
# CACHE EM MEMÓRIA
# ============================================================================

class DataCache:
    """Cache simples em memória para melhorar performance"""
    
    def __init__(self):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.max_age_seconds = 3600  # 1 hora
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self.max_age_seconds:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())
    
    def clear(self):
        self.cache.clear()

cache = DataCache()

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def normalize_cpf(cpf: str) -> str:
    """Normaliza CPF removendo formatação"""
    cpf_clean = re.sub(r'\D', '', cpf)
    if len(cpf_clean) != 11:
        raise ValueError(f"CPF inválido: {cpf}")
    return cpf_clean

def detect_search_type(value: str) -> str:
    """Detecta se é CPF ou CONTATOS_ID"""
    value_clean = value.strip()
    
    # Tentar normalizar como CPF
    try:
        normalize_cpf(value_clean)
        return "CPF"
    except:
        pass
    
    # Verificar se é numérico (CONTATOS_ID)
    if value_clean.isdigit():
        return "CONTATOS_ID"
    
    raise ValueError(f"Valor inválido: {value}")

def execute_query_with_timeout(
    db_path: str,
    query: str,
    params: Tuple = (),
    timeout: int = 5
) -> List[Dict[str, Any]]:
    """Executa query com timeout e tratamento de erro"""
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    except sqlite3.OperationalError as e:
        logger.error(f"Erro operacional em {db_path}: {e}")
        raise
    except sqlite3.DatabaseError as e:
        logger.error(f"Erro de banco de dados em {db_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado em {db_path}: {e}")
        raise

def get_contatos_id_by_cpf(cpf: str) -> Optional[str]:
    """Obtém CONTATOS_ID a partir de CPF"""
    try:
        db_config = DATABASES["contatos"]
        query = f"SELECT CONTATOS_ID FROM {db_config['table']} WHERE CPF = ? LIMIT 1"
        data = execute_query_with_timeout(db_config["file"], query, (cpf,), timeout=5)
        
        if data and "CONTATOS_ID" in data[0]:
            return str(data[0]["CONTATOS_ID"])
    except Exception as e:
        logger.error(f"Erro ao obter CONTATOS_ID: {e}")
    
    return None

def get_cpf_by_contatos_id(contatos_id: str) -> Optional[str]:
    """Obtém CPF a partir de CONTATOS_ID"""
    try:
        db_config = DATABASES["contatos"]
        query = f"SELECT CPF FROM {db_config['table']} WHERE CONTATOS_ID = ? LIMIT 1"
        data = execute_query_with_timeout(db_config["file"], query, (contatos_id,), timeout=5)
        
        if data and "CPF" in data[0]:
            return str(data[0]["CPF"])
    except Exception as e:
        logger.error(f"Erro ao obter CPF: {e}")
    
    return None

def search_in_database(
    db_name: str,
    db_config: Dict,
    key_value: str,
    limit: int = 100,
    search_by_cpf: bool = False
) -> Dict[str, Any]:
    """Busca em um banco de dados específico usando CONTATOS_ID ou DocNumber"""
    
    result = {
        "description": db_config["description"],
        "status": "error",
        "count": 0,
        "data": [],
        "error": None
    }
    
    try:
        # Validar arquivo
        if not os.path.exists(db_config["file"]):
            result["error"] = f"Arquivo não encontrado"
            return result
        
        # Construir query
        key_field = db_config["key_field"]
        table = db_config["table"]
        
        # Se é busca por CPF no banco de contatos, usar CPF como campo
        if search_by_cpf and db_name == "contatos":
            query = f"SELECT * FROM {table} WHERE CPF = ? LIMIT ?"
        else:
            query = f"SELECT * FROM {table} WHERE {key_field} = ? LIMIT ?"
        
        # Executar query
        data = execute_query_with_timeout(
            db_config["file"],
            query,
            (key_value, limit),
            timeout=5
        )
        
        # Limitar dados retornados para performance
        result["status"] = "success"
        result["count"] = len(data)
        result["data"] = data[:10]  # Retornar máximo 10 registros
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Erro ao buscar em {db_name}: {e}")
    
    return result

def search_all_databases_by_contatos_id(
    contatos_id: str,
    limit: int = 100
) -> Dict[str, Dict]:
    """Busca em todos os bancos usando CONTATOS_ID"""
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        # Buscar em contatos, poder_aquisitivo e historico_telefones
        for db_name in ["contatos", "poder_aquisitivo", "historico_telefones"]:
            db_config = DATABASES[db_name]
            future = executor.submit(
                search_in_database,
                db_name,
                db_config,
                contatos_id,
                limit
            )
            futures[future] = db_name
        
        for future in as_completed(futures):
            db_name = futures[future]
            try:
                results[db_name] = future.result()
            except Exception as e:
                logger.error(f"Erro ao buscar em {db_name}: {e}")
                results[db_name] = {
                    "description": DATABASES[db_name]["description"],
                    "status": "error",
                    "count": 0,
                    "data": [],
                    "error": str(e)
                }
    
    return results

def search_irpf_by_cpf(cpf: str, limit: int = 100) -> Dict[str, Any]:
    """Busca em IRPF usando CPF (DocNumber)"""
    
    return search_in_database(
        "irpf",
        DATABASES["irpf"],
        cpf,
        limit
    )

def search_all_databases_by_cpf(
    cpf: str,
    limit: int = 100
) -> Dict[str, Dict]:
    """Busca em todos os bancos usando CPF"""
    
    results = {}
    
    # Passo 1: Buscar em contatos para obter CONTATOS_ID (usando CPF como campo)
    contatos_result = search_in_database(
        "contatos",
        DATABASES["contatos"],
        cpf,
        limit,
        search_by_cpf=True
    )
    results["contatos"] = contatos_result
    
    # Se encontrou contato, buscar nos outros bancos
    if contatos_result["status"] == "success" and contatos_result["count"] > 0:
        contatos_id = str(contatos_result["data"][0]["CONTATOS_ID"])
        
        # Buscar em poder_aquisitivo e historico_telefones usando CONTATOS_ID
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            
            for db_name in ["poder_aquisitivo", "historico_telefones"]:
                db_config = DATABASES[db_name]
                future = executor.submit(
                    search_in_database,
                    db_name,
                    db_config,
                    contatos_id,
                    limit
                )
                futures[future] = db_name
            
            # Buscar em IRPF usando CPF
            irpf_future = executor.submit(search_irpf_by_cpf, cpf, limit)
            futures[irpf_future] = "irpf"
            
            for future in as_completed(futures):
                db_name = futures[future]
                try:
                    results[db_name] = future.result()
                except Exception as e:
                    logger.error(f"Erro ao buscar em {db_name}: {e}")
                    results[db_name] = {
                        "description": DATABASES[db_name]["description"],
                        "status": "error",
                        "count": 0,
                        "data": [],
                        "error": str(e)
                    }
    else:
        # Se não encontrou em contatos, retornar erros para os outros
        results["poder_aquisitivo"] = {
            "description": DATABASES["poder_aquisitivo"]["description"],
            "status": "error",
            "count": 0,
            "data": [],
            "error": "CPF não encontrado em contatos"
        }
        results["historico_telefones"] = {
            "description": DATABASES["historico_telefones"]["description"],
            "status": "error",
            "count": 0,
            "data": [],
            "error": "CPF não encontrado em contatos"
        }
        results["irpf"] = search_irpf_by_cpf(cpf, limit)
    
    return results

def validate_consistency(results: Dict[str, Dict]) -> Dict[str, Any]:
    """Valida consistência dos dados retornados"""
    
    consistency_report = {
        "valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Verificar se pelo menos um banco retornou dados
    total_records = sum(r.get("count", 0) for r in results.values())
    
    if total_records == 0:
        consistency_report["errors"].append("Nenhum dado encontrado em nenhum banco")
        consistency_report["valid"] = False
    
    # Verificar erros em bancos específicos
    for db_name, result in results.items():
        if result.get("status") == "error":
            consistency_report["warnings"].append(
                f"{db_name}: {result.get('error', 'Erro desconhecido')}"
            )
    
    return consistency_report

# ============================================================================
# APLICAÇÃO FASTAPI
# ============================================================================

app = FastAPI(
    title="API de Cruzamento de Dados V4",
    description="Sistema inteligente com queries otimizadas e cruzamento correto",
    version="4.0.0"
)

@app.get("/")
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "name": "API de Cruzamento de Dados Multi-Banco (V4 - Inteligente)",
        "version": "4.0.0",
        "description": "Sistema com queries otimizadas, cache e cruzamento inteligente",
        "features": [
            "Busca inteligente com auto-detecção de tipo",
            "Cache em memória para performance",
            "Processamento paralelo de bancos",
            "Cruzamento inteligente por CONTATOS_ID e CPF",
            "Validação de consistência",
            "Tratamento robusto de erros"
        ],
        "endpoints": {
            "/search/{value}": "Busca inteligente (auto-detecta CPF ou CONTATOS_ID)",
            "/contatos/{contatos_id}": "Busca por CONTATOS_ID específico",
            "/cpf/{cpf}": "Busca por CPF",
            "/databases": "Lista bancos de dados disponíveis",
            "/health": "Health check",
            "/docs": "Documentação interativa (Swagger UI)",
        },
        "databases": {name: db["description"] for name, db in DATABASES.items()}
    }

@app.get("/health")
async def health_check():
    """Health check da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "API V4 está rodando com otimizações ativas",
        "cache_size": len(cache.cache),
        "databases_configured": len(DATABASES)
    }

@app.get("/databases")
async def list_databases():
    """Lista todos os bancos de dados disponíveis"""
    return {
        "databases": {
            name: {
                "description": db["description"],
                "table": db["table"],
                "key_field": db["key_field"],
            }
            for name, db in DATABASES.items()
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/search/{value}")
async def search(
    value: str,
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados por banco")
):
    """
    Busca inteligente que auto-detecta CPF ou CONTATOS_ID
    
    Parâmetros:
    - value: CPF (com ou sem formatação) ou CONTATOS_ID
    - limit: Limite de resultados (1-1000, padrão 100)
    """
    
    start_time = time.time()
    
    try:
        # Detectar tipo de busca
        search_type = detect_search_type(value)
        
        # Verificar cache
        cache_key = f"{search_type}:{value}:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            cached_result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return cached_result
        
        # Buscar em todos os bancos
        if search_type == "CPF":
            cpf_normalized = normalize_cpf(value)
            results = search_all_databases_by_cpf(cpf_normalized, limit)
        else:  # CONTATOS_ID
            results = search_all_databases_by_contatos_id(value, limit)
        
        # Validar consistência
        consistency = validate_consistency(results)
        
        # Montar resposta
        response = {
            "search_type": search_type,
            "search_value": value,
            "timestamp": datetime.now().isoformat(),
            "databases": results,
            "summary": {
                "total_databases_queried": len(DATABASES),
                "successful_queries": sum(1 for r in results.values() if r.get("status") == "success"),
                "failed_queries": sum(1 for r in results.values() if r.get("status") == "error"),
                "total_records": sum(r.get("count", 0) for r in results.values())
            },
            "consistency": consistency,
            "from_cache": False,
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        # Cachear resultado
        cache.set(cache_key, response)
        
        # Validar antes de retornar
        if not consistency["valid"] and consistency["errors"]:
            raise HTTPException(
                status_code=404,
                detail=f"Dados não encontrados: {consistency['errors'][0]}"
            )
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro em /search: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/cpf/{cpf}")
async def search_by_cpf(
    cpf: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """Busca específica por CPF"""
    
    try:
        normalize_cpf(cpf)
        return await search(cpf, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/contatos/{contatos_id}")
async def search_by_contatos_id(
    contatos_id: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """Busca específica por CONTATOS_ID"""
    
    if not contatos_id.isdigit():
        raise HTTPException(status_code=400, detail="CONTATOS_ID deve ser numérico")
    
    return await search(contatos_id, limit)

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando API de Cruzamento de Dados V4...")
    print("📊 Bancos configurados:", len(DATABASES))
    print("⚡ Otimizações ativas: Cache, Processamento Paralelo, Cruzamento Inteligente")
    print("🌐 Acesse a documentação em: http://0.0.0.0:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
