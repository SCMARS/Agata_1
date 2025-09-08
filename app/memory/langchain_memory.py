"""
LangChain-powered Intelligent Memory System
Использует Chroma DB, OpenAI Embeddings и RAG для интеллектуального поиска
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

# LangChain imports
try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain.chains import RetrievalQA
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    print(f"⚠️ LangChain components not available: {e}")

# Project imports
from .base import MemoryAdapter, Message, MemoryContext

class LangChainMemory(MemoryAdapter):
    """
    Интеллектуальная память на основе LangChain
    Поддерживает векторный поиск, RAG и автоматическую суммаризацию
    """
    
    def __init__(self, user_id: str, max_memories: int = 1000):
        super().__init__(user_id)
        self.user_id = user_id
        self.max_memories = max_memories
        
        # Настройка логирования
        self.logger = logging.getLogger(f"{__name__}.{user_id}")
        
        # Инициализируем компоненты LangChain
        if not LANGCHAIN_AVAILABLE:
            self.logger.error("LangChain not available, LangChainMemory will be limited")
            self.vector_store = None
            self.embeddings = None
            self.llm = None
            self.qa_chain = None
            return
        
        # Настройки из переменных окружения
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.error("OPENAI_API_KEY not found")
            self.vector_store = None
            self.embeddings = None
            self.llm = None
            self.qa_chain = None
            return
        
        # Конфигурация
        self.config = self._load_config()
        
        # Инициализация компонентов
        self._initialize_embeddings()
        self._initialize_vector_store()
        self._initialize_llm()
        self._initialize_text_splitter()
        self._initialize_rag_chain()
        
        # Метрики
        self.metrics = {
            'documents_added': 0,
            'searches_performed': 0,
            'rag_queries': 0,
            'summaries_created': 0
        }
        
        self.logger.info(f"LangChainMemory initialized for user {user_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию без хардкода"""
        try:
            # Пытаемся загрузить из ProductionConfigManager
            from ..config.production_config_manager import get_config
            return get_config('langchain_memory', self.user_id, self._get_default_config())
        except ImportError:
            # Fallback к переменным окружения
            return {
                'embedding_model': os.getenv('LANGCHAIN_EMBEDDING_MODEL', 'text-embedding-3-small'),
                'llm_model': os.getenv('LANGCHAIN_LLM_MODEL', 'gpt-4o-mini'),
                'chunk_size': int(os.getenv('LANGCHAIN_CHUNK_SIZE', '1000')),
                'chunk_overlap': int(os.getenv('LANGCHAIN_CHUNK_OVERLAP', '200')),
                'temperature': float(os.getenv('LANGCHAIN_TEMPERATURE', '0.7')),
                'max_tokens': int(os.getenv('LANGCHAIN_MAX_TOKENS', '500')),
                'collection_name': f"agata_memory_{self.user_id}",
                'persist_directory': os.getenv('CHROMA_PERSIST_DIR', './chroma_db'),
                'search_k': int(os.getenv('LANGCHAIN_SEARCH_K', '5')),
                'score_threshold': float(os.getenv('LANGCHAIN_SCORE_THRESHOLD', '0.7'))
            }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            'embedding_model': 'text-embedding-3-small',
            'llm_model': 'gpt-4o-mini',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'temperature': 0.7,
            'max_tokens': 500,
            'collection_name': f"agata_memory_{self.user_id}",
            'persist_directory': './chroma_db',
            'search_k': 5,
            'score_threshold': 0.7
        }
    
    def _initialize_embeddings(self):
        """Инициализирует embeddings"""
        try:
            self.embeddings = OpenAIEmbeddings(
                model=self.config['embedding_model'],
                api_key=self.api_key
            )
            self.logger.info(f"Embeddings initialized: {self.config['embedding_model']}")
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None
    
    def _initialize_vector_store(self):
        """Инициализирует Chroma vector store"""
        try:
            if not self.embeddings:
                self.vector_store = None
                return
            
            # Создаем директорию если не существует
            persist_dir = Path(self.config['persist_directory'])
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            self.vector_store = Chroma(
                collection_name=self.config['collection_name'],
                embedding_function=self.embeddings,
                persist_directory=str(persist_dir)
            )
            self.logger.info(f"Vector store initialized: {self.config['collection_name']}")
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store = None
    
    def _initialize_llm(self):
        """Инициализирует LLM"""
        try:
            self.llm = ChatOpenAI(
                model=self.config['llm_model'],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens'],
                api_key=self.api_key
            )
            self.logger.info(f"LLM initialized: {self.config['llm_model']}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    def _initialize_text_splitter(self):
        """Инициализирует text splitter"""
        try:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config['chunk_size'],
                chunk_overlap=self.config['chunk_overlap']
            )
            self.logger.info("Text splitter initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize text splitter: {e}")
            self.text_splitter = None
    
    def _initialize_rag_chain(self):
        """Инициализирует RAG chain"""
        try:
            if not self.vector_store or not self.llm:
                self.qa_chain = None
                return
            
            # Создаем retriever
            retriever = self.vector_store.as_retriever(
                search_kwargs={
                    "k": self.config['search_k'],
                    "score_threshold": self.config['score_threshold']
                }
            )
            
            # Создаем RAG chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            self.logger.info("RAG chain initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize RAG chain: {e}")
            self.qa_chain = None
    
    def add_message(self, message: Message, context: MemoryContext) -> None:
        """Добавляет сообщение в память"""
        try:
            if not self.vector_store or not self.text_splitter:
                self.logger.warning("Vector store not available, message not stored")
                return
            
            # Создаем документ из сообщения
            content = f"[{message.role}] {message.content}"
            metadata = {
                'user_id': self.user_id,
                'role': message.role,
                'timestamp': message.timestamp.isoformat(),
                'day_number': context.day_number,
                'conversation_id': context.conversation_id or 'default',
                **message.metadata
            }
            
            # Разбиваем на чанки если текст длинный
            if len(content) > self.config['chunk_size']:
                docs = self.text_splitter.create_documents([content], [metadata])
            else:
                docs = [Document(page_content=content, metadata=metadata)]
            
            # Добавляем в vector store
            self.vector_store.add_documents(docs)
            
            self.metrics['documents_added'] += len(docs)
            self.logger.debug(f"Added {len(docs)} documents to vector store")
            
        except Exception as e:
            self.logger.error(f"Failed to add message to vector store: {e}")
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Выполняет семантический поиск в памяти"""
        try:
            if not self.vector_store:
                self.logger.warning("Vector store not available for search")
                return []
            
            # Выполняем similarity search с оценками
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query, 
                k=limit
            )
            
            results = []
            for doc, score in docs_with_scores:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'relevance_score': float(1.0 - score),  # Инвертируем distance в relevance
                    'timestamp': doc.metadata.get('timestamp'),
                    'role': doc.metadata.get('role', 'unknown')
                })
            
            self.metrics['searches_performed'] += 1
            self.logger.debug(f"Search performed: found {len(results)} results")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def get_context(self, context: MemoryContext) -> str:
        """Получает контекст для промпта"""
        try:
            if not self.vector_store:
                return "Векторная память недоступна."
            
            # Поиск релевантных сообщений
            recent_query = f"пользователь день {context.day_number}"
            results = self.search_memory(recent_query, limit=5)
            
            if not results:
                return "История разговоров пуста."
            
            # Формируем контекст
            context_parts = ["Релевантная история разговоров:"]
            for result in results:
                content = result['content']
                score = result['relevance_score']
                timestamp = result.get('timestamp', '')
                context_parts.append(f"[{score:.2f}] {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to get context: {e}")
            return "Ошибка получения контекста."
    
    def generate_rag_response(self, query: str) -> Dict[str, Any]:
        """Генерирует ответ используя RAG"""
        try:
            if not self.qa_chain:
                return {
                    'answer': 'RAG система недоступна',
                    'sources': [],
                    'success': False
                }
            
            # Выполняем RAG запрос
            result = self.qa_chain({"query": query})
            
            # Извлекаем источники
            sources = []
            if 'source_documents' in result:
                for doc in result['source_documents']:
                    sources.append({
                        'content': doc.page_content,
                        'metadata': doc.metadata
                    })
            
            self.metrics['rag_queries'] += 1
            
            return {
                'answer': result.get('result', 'Не удалось получить ответ'),
                'sources': sources,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"RAG query failed: {e}")
            return {
                'answer': f'Ошибка RAG запроса: {e}',
                'sources': [],
                'success': False
            }
    
    def summarize_conversation(self, messages: List[Message]) -> str:
        """Суммаризует разговор"""
        try:
            if not self.llm or not messages:
                return "Нет сообщений для суммаризации."
            
            # Формируем промпт для суммаризации
            conversation_text = "\n".join([
                f"{msg.role}: {msg.content}" for msg in messages[-10:]  # Последние 10
            ])
            
            prompt = ChatPromptTemplate.from_template(
                "Создай краткое резюме следующего разговора:\n\n{conversation}\n\n"
                "Резюме должно включать:\n"
                "1. Основные темы обсуждения\n"
                "2. Ключевые факты о пользователе\n"
                "3. Эмоциональный тон разговора\n"
                "4. Важные детали для продолжения\n\n"
                "Резюме:"
            )
            
            chain = prompt | self.llm | StrOutputParser()
            summary = chain.invoke({"conversation": conversation_text})
            
            self.metrics['summaries_created'] += 1
            return summary
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            return f"Ошибка суммаризации: {e}"
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Добавляет документ в векторную БД"""
        try:
            if not self.vector_store or not self.text_splitter:
                return False
            
            # Подготавливаем метаданные
            doc_metadata = {
                'user_id': self.user_id,
                'type': 'document',
                'added_at': datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Создаем документы
            docs = self.text_splitter.create_documents([content], [doc_metadata])
            
            # Добавляем в store
            self.vector_store.add_documents(docs)
            
            self.metrics['documents_added'] += len(docs)
            self.logger.info(f"Added document with {len(docs)} chunks")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add document: {e}")
            return False
    
    def clear_memory(self) -> None:
        """Очищает память пользователя"""
        try:
            if not self.vector_store:
                return
            
            # Получаем все документы пользователя
            results = self.vector_store.get(
                where={"user_id": self.user_id}
            )
            
            if results and 'ids' in results:
                # Удаляем документы
                self.vector_store.delete(ids=results['ids'])
                self.logger.info(f"Cleared {len(results['ids'])} documents from memory")
            
        except Exception as e:
            self.logger.error(f"Failed to clear memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику работы"""
        try:
            # Базовые метрики
            stats = dict(self.metrics)
            
            if self.vector_store:
                # Статистика коллекции
                try:
                    collection_info = self.vector_store.get()
                    stats['total_documents'] = len(collection_info.get('ids', []))
                except:
                    stats['total_documents'] = 'unknown'
            else:
                stats['total_documents'] = 0
            
            stats['components_status'] = {
                'embeddings': self.embeddings is not None,
                'vector_store': self.vector_store is not None,
                'llm': self.llm is not None,
                'qa_chain': self.qa_chain is not None
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Проверяет здоровье всех компонентов"""
        health = {
            'status': 'healthy',
            'components': {},
            'config': {
                'model': self.config.get('llm_model', 'unknown'),
                'embeddings': self.config.get('embedding_model', 'unknown')
            }
        }
        
        try:
            # Проверяем embeddings
            if self.embeddings:
                test_embedding = self.embeddings.embed_query("test")
                health['components']['embeddings'] = len(test_embedding) > 0
            else:
                health['components']['embeddings'] = False
            
            # Проверяем vector store
            if self.vector_store:
                try:
                    self.vector_store.get(limit=1)
                    health['components']['vector_store'] = True
                except:
                    health['components']['vector_store'] = False
            else:
                health['components']['vector_store'] = False
            
            # Проверяем LLM
            health['components']['llm'] = self.llm is not None
            health['components']['qa_chain'] = self.qa_chain is not None
            
            # Общий статус
            if not all(health['components'].values()):
                health['status'] = 'degraded'
            
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health
