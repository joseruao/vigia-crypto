import sys
import traceback

print("=== DEBUG START ===")

try:
    print("1. Tentando importar Api.main...")
    from Api import main
    print("✅ Import bem sucedido!")
    
    print("2. Tentando executar servidor...")
    import uvicorn
    uvicorn.run(main.app, host="127.0.0.1", port=8000, log_level="info")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    print("Traceback completo:")
    traceback.print_exc()

print("=== DEBUG END ===")