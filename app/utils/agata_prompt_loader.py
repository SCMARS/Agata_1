"""
Система загрузки промптов Агаты из файлов конфигурации
"""
import os
import logging
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class AgataPromptLoader:
    """Загрузчик промптов Агаты из файловой структуры"""
    
    def __init__(self, base_path: str = "agata_prompt_data"):
        self.base_path = Path(base_path)
        self.persona_cache = {}
        self.style_cache = {}
        self.stage_cache = {}
        
    def load_limited_knowledge(self) -> str:
        """Загружает правила ограниченного знания из 10_limited_knowledge.txt"""
        if 'limited_knowledge' in self.persona_cache:
            return self.persona_cache['limited_knowledge']
            
        knowledge_file = "10_limited_knowledge.txt"  
        if os.path.exists(knowledge_file):
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.persona_cache['limited_knowledge'] = content
                    logger.info(f"Загружен файл ограниченного знания: {knowledge_file}")
                    return content
            except Exception as e:
                logger.error(f"Ошибка загрузки {knowledge_file}: {e}")
        
        logger.warning(f"Файл {knowledge_file} не найден")
        return ""

    def load_persona_bio(self) -> str:

        if 'full_bio' in self.persona_cache:
            return self.persona_cache['full_bio']
            
        persona_dir = self.base_path / "persona"
        if not persona_dir.exists():
            logger.error(f"Директория persona не найдена: {persona_dir}")
            return self._get_fallback_bio()
            
        bio_parts = []
        
        # Загружаем файлы биографии в правильном порядке
        bio_files = [
            "agata_bio_01_childhood.txt",
            "agata_bio_02_study_and_first_job.txt", 
            "agata_bio_03_move_to_warsaw.txt",
            "agata_bio_04_career_growth.txt",
            "agata_bio_05_appearance_health.txt",
            "agata_bio_06_lifestyle_trading.txt",
            "agata_bio_07_personal_life.txt",
            "agata_bio_08_character.txt"
        ]
        
        for filename in bio_files:
            file_path = persona_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            bio_parts.append(content)
                            logger.info(f"Загружен файл биографии: {filename}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки {filename}: {e}")
        
        if not bio_parts:
            logger.warning("Не удалось загрузить файлы биографии, используем fallback")
            return self._get_fallback_bio()
            
        full_bio = "\n\n".join(bio_parts)
        self.persona_cache['full_bio'] = full_bio
        
        logger.info(f"Загружена полная биография Агаты: {len(full_bio)} символов")
        return full_bio
    
    def load_style_guidelines(self) -> Dict[str, str]:
        """Загружает руководства по стилю общения"""
        if 'style_guidelines' in self.style_cache:
            return self.style_cache['style_guidelines']
            
        style_dir = self.base_path / "style"
        guidelines = {}
        
        style_files = [
            "style_core.txt",
            "style_empathy.txt", 
            "style_etiquette.txt",
            "style_humor.txt"
        ]
        
        for filename in style_files:
            file_path = style_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        key = filename.replace('style_', '').replace('.txt', '')
                        guidelines[key] = content
                        logger.info(f"Загружен стиль: {key}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки {filename}: {e}")
        
        self.style_cache['style_guidelines'] = guidelines
        return guidelines
    
    def load_stage_prompt(self, stage_number: int) -> str:
        """Загружает промпт для определенного этапа общения"""
        cache_key = f'stage_{stage_number}'
        if cache_key in self.stage_cache:
            return self.stage_cache[cache_key]
            
        stage_dir = self.base_path / "stages"
        stage_file = stage_dir / f"stage_{stage_number}.txt"
        
        if not stage_file.exists():
            logger.warning(f"Файл этапа не найден: {stage_file}")
            return self._get_fallback_stage_prompt(stage_number)
            
        try:
            with open(stage_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.stage_cache[cache_key] = content
                logger.info(f"Загружен промпт для этапа {stage_number}")
                return content
        except Exception as e:
            logger.error(f"Ошибка загрузки stage_{stage_number}.txt: {e}")
            return self._get_fallback_stage_prompt(stage_number)
    
    def create_system_prompt(self, stage_number: int = 1, day_number: int = 1, memory_context: str = "") -> str:
        """Создает системный промпт, используя новый живой стиль общения"""
        
        # Загружаем новый системный промпт из config/prompts/system_core.txt
        system_core_path = "config/prompts/system_core.txt"
        if os.path.exists(system_core_path):
            try:
                with open(system_core_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read().strip()
                    # Добавляем информацию о дне в промпт
                    day_prompt = self._get_day_prompt(day_number)
                    day_info = f"\n\n=== ТЕКУЩИЙ ДЕНЬ ОБЩЕНИЯ ===\n{day_prompt}\n"
                    system_prompt = system_prompt.replace("=== ТЕКУЩИЙ ЭТАП ОБЩЕНИЯ ===", f"{day_info}=== ТЕКУЩИЙ ЭТАП ОБЩЕНИЯ ===")
                    logger.info(f"Загружен новый системный промпт из {system_core_path} с днем {day_number}")
                    return system_prompt
            except Exception as e:
                logger.error(f"Ошибка загрузки {system_core_path}: {e}")
        
        # Fallback к старому методу
        logger.warning("Используем fallback системный промпт")
        bio = self.load_persona_bio()
        style_guidelines = self.load_style_guidelines()
        stage_prompt = self.load_stage_prompt(stage_number)
        limited_knowledge = self.load_limited_knowledge()
        
        # Формируем основной промпт с четким разделением
        system_prompt = f"""ТЫ — Агата Кузьменко:

=== ТВОЯ БИОГРАФИЯ И ЛИЧНОСТЬ (ПРО СЕБЯ) ===
{bio}

=== ПРАВИЛА ОГРАНИЧЕННОГО ЗНАНИЯ ===
{limited_knowledge}

=== ПРАВИЛА СТИЛЯ ОБЩЕНИЯ ===
{style_guidelines.get('core', 'Общайся естественно и дружелюбно.')}

{style_guidelines.get('empathy', '')}

{style_guidelines.get('etiquette', '')}

{style_guidelines.get('humor', '')}

=== ТЕКУЩИЙ ЭТАП ОБЩЕНИЯ (День {day_number}) ===
{stage_prompt}

=== ВАЖНЫЕ ПРИНЦИПЫ ===
- НИКОГДА не путай свою биографию с информацией о пользователе
- Твоя биография (выше) - это информация О ТЕБЕ (Агате)
- Информация о пользователе поступает из ПАМЯТИ - используй её для персонализации
- НЕ приписывай пользователю свои увлечения (маркетинг, трейдинг, йога)
- Отвечай естественно, как живой человек
- Проявляй эмпатию и интерес к собеседнику
- Поддерживай живой диалог, но не задавай вопросы слишком часто
- Помни о временном контексте (время суток, перерывы в общении)

=== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ (ИЗ ПАМЯТИ) ===
{memory_context if memory_context else "Пока нет информации о пользователе."}

ИСПОЛЬЗУЙ ТОЛЬКО ЭТУ ИНФОРМАЦИЮ для ответов о пользователе, НЕ свою биографию.
"""
        
        logger.info(f"Создан fallback системный промпт для дня {day_number}, этапа {stage_number}")
        return system_prompt
    
    def _get_fallback_bio(self) -> str:
        """Fallback биография если файлы не загрузились"""
        return """Агата Кузьменко, 27 лет, родилась в Киеве, живет в Варшаве с 2018 года.
Маркетолог, работаю в Move Closer, занимаюсь трейдингом. 
Хобби: спорт (бассейн, спортзал), кулинария, путешествия.
Мечтаю о Tesla, планирую свое агентство.

Личность: тёплая, эмпатичная, профессиональная, но не техническая.
Стиль общения: дружелюбный, естественный, без канцелярита.
Роль: маркетолог-партнёр, а не программист или техник."""
    
    def _get_fallback_stage_prompt(self, stage_number: int) -> str:
        """Fallback промпт для этапа"""
        stage_prompts = {
            1: "Знакомство и установление контакта. Будь открытой и дружелюбной.",
            2: "Углубление отношений. Проявляй больше интереса к собеседнику.",
            3: "Доверительное общение. Можешь делиться личными мыслями."
        }
        return stage_prompts.get(stage_number, "Поддерживай естественное общение.")
    
    def clear_cache(self):
        """Очищает кеш промптов"""
        self.persona_cache.clear()
        self.style_cache.clear() 
        self.stage_cache.clear()
        logger.info("Кеш промптов очищен")
    
    def _get_day_prompt(self, day_number: int) -> str:
        """Получить промпт для конкретного дня"""
        try:
            # Определяем файл промпта для дня
            if day_number <= 7:
                prompt_file = f"day_{day_number}.txt"
            elif day_number <= 14:
                prompt_file = "day_7.txt"
            elif day_number <= 30:
                prompt_file = "day_7.txt"  # Используем day_7 для всех дней 8-30
            else:
                prompt_file = "day_7.txt"  # Для дней 30+
            
            prompt_path = os.path.join("config", "prompts", prompt_file)
            
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f"День {day_number} знакомства\n\n{f.read().strip()}"
            else:
                return f"День {day_number} знакомства"
                
        except Exception as e:
            logger.error(f"Ошибка загрузки day_{day_number} prompt: {e}")
            return f"День {day_number} знакомства"

# Глобальный экземпляр загрузчика
agata_loader = AgataPromptLoader()
