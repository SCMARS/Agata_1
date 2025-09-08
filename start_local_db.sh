#!/bin/bash

echo "🚀 Запускаем локальную PostgreSQL с pgvector..."

# Проверяем, установлен ли PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL не установлен!"
    echo "💡 Установите PostgreSQL: brew install postgresql"
    echo "💡 Или используйте Docker: docker run --name postgres-pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d pgvector/pgvector:pg15"
    exit 1
fi

# Проверяем, запущен ли PostgreSQL
if pg_isready -h localhost -p 5432 &> /dev/null; then
    echo "✅ PostgreSQL уже запущен на localhost:5432"
else
    echo "🔄 Запускаем PostgreSQL..."
    brew services start postgresql
    sleep 3
fi

# Создаем базу данных если её нет
echo "🔍 Проверяем базу данных..."
if ! psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw agatha; then
    echo "📝 Создаем базу данных 'agatha'..."
    createdb -h localhost -U postgres agatha
    echo "✅ База данных 'agatha' создана"
else
    echo "✅ База данных 'agatha' уже существует"
fi

# Проверяем расширение pgvector
echo "🔍 Проверяем расширение pgvector..."
if psql -h localhost -U postgres -d agatha -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
    echo "✅ Расширение pgvector уже установлено"
else
    echo "⚠️ Расширение pgvector не установлено"
    echo "💡 Установите pgvector: brew install pgvector"
    echo "💡 Или используйте Docker образ с pgvector"
fi

echo "🎯 Готово! База данных доступна на localhost:5432"
echo "📊 Подключение: postgresql://postgres:postgres@localhost:5432/agatha" 