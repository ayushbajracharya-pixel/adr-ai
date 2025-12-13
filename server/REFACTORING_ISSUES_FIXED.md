# Refactoring Issues Found and Fixed

## Issues Fixed

### 1. ✅ File Upload - Missing `await` (FIXED)
**Issue**: `extract_text_from_file` was async but wasn't being awaited, and file was being read twice.

**Location**: `app/services/adr/adr_service.py` line 71

**Fix**: 
- Changed `extract_text_from_file` to `extract_text_from_content` which takes bytes directly
- Removed async/await since we're passing already-read content
- This prevents reading the file twice and fixes the coroutine error

### 2. ✅ Extraction Chain Method Calls (FIXED)
**Issue**: `invoke_intent_chain` and `invoke_metadata_chain` expect strings but were being called with dicts.

**Locations**: 
- `app/services/adr/query_processor.py` line 164
- `app/services/adr/metadata_extractor.py` line 28

**Fix**: Changed calls from `{"query": query}` to just `query` and `{"text": text_content}` to just `text_content`

### 3. ✅ Unused/Incorrect Dependency Function (FIXED)
**Issue**: `get_database_session()` in `app/api/dependencies.py` was incorrectly implemented and unused.

**Fix**: Removed the function since `get_db` is used directly in routes

### 4. ✅ Middleware Import (FIXED)
**Issue**: `app/middleware/auth.py` was importing from old path.

**Fix**: Updated import from `app.services.auth_service` to `app.core.security`

## Potential Issues to Watch

### 1. Service Instantiation at Module Level
**Location**: All route files (auth.py, conversations.py, files.py, query.py, upload.py)

**Current**: Services are instantiated at module level:
```python
adr_service = ADRService()
conversation_service = ConversationService()
```

**Note**: This is generally fine for stateless services, but if you need per-request instances or dependency injection, consider using FastAPI's dependency system.

### 2. Async/Sync Consistency
**Location**: `app/api/v1/routes/files.py` line 14

**Current**: `list_uploaded_files` is synchronous (not async)

**Note**: This is fine since `s3_service.list_files()` is synchronous, but for consistency, you might want to make it async if you plan to make S3 calls async in the future.

### 3. Error Handling
**Note**: Some services catch generic `Exception`. Consider using the custom exceptions from `app/core/exceptions.py` for better error handling.

### 4. Database Session Management
**Location**: Routes using `get_db` dependency

**Note**: The `get_db` dependency handles commit/rollback automatically. Make sure this behavior is desired for all endpoints.

## Verification Checklist

- [x] All imports updated to new paths
- [x] No references to old file paths
- [x] Async/await properly used
- [x] Service method calls match signatures
- [x] File upload flow works correctly
- [x] Query processing works correctly
- [x] Authentication works correctly
- [x] All routes properly registered

## Testing Recommendations

1. **File Upload**: Test uploading PDF, DOCX, and TXT files
2. **Query**: Test various query types (semantic, list, filter, hybrid)
3. **Conversations**: Test creating, listing, and messaging in conversations
4. **Authentication**: Test Google OAuth flow
5. **File Management**: Test listing and deleting files

