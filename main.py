from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
from PyPDF2 import PdfMerger

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Etiqueta E</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .etiqueta-e { background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .remember-box { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #9b59b6; }
        .feature { display: flex; align-items: center; margin: 10px 0; }
        .feature-icon { font-size: 24px; margin-right: 15px; }
        textarea { width: 100%; height: 200px; padding: 15px; font-family: monospace; border: 2px solid #e9ecef; border-radius: 8px; }
        button { width: 100%; padding: 20px; font-size: 18px; background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; border: none; border-radius: 8px; cursor: pointer; margin: 10px 0; font-weight: bold; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(155, 89, 182, 0.4); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }
        .result { margin-top: 20px; padding: 20px; border-radius: 8px; }
        .success { background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; }
        .error { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; }
        .processing { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; }
        .etiqueta-preview { background: #fff; border: 2px solid #9b59b6; border-radius: 8px; padding: 20px; margin: 15px 0; text-align: center; }
        .big-e { font-size: 72px; font-weight: bold; color: #9b59b6; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Versão com Etiqueta "E" Separadora</p>
    </div>
    
    <div class="etiqueta-e">
        <h2>🎯 Lembrou da Etiqueta "E"!</h2>
        <p><strong>Sistema original</strong> • <strong>Etiqueta "E" automática</strong> • <strong>Separação perfeita</strong></p>
    </div>
    
    <div class="remember-box">
        <h3>💭 Como era antes (que funcionava):</h3>
        <div class="feature">
            <div class="feature-icon">🔍</div>
            <div><strong>Detecção automática:</strong> Primeira linha de cada bloco ZPL</div>
        </div>
        <div class="feature">
            <div class="feature-icon">📄</div>
            <div><strong>Etiqueta "E":</strong> Inserida automaticamente entre SKUs diferentes</div>
        </div>
        <div class="feature">
            <div class="feature-icon">⚡</div>
            <div><strong>Processamento direto:</strong> Simples e funcional como antes</div>
        </div>
        <div class="feature">
            <div class="feature-icon">📏</div>
            <div><strong>Medidas 8×2,5cm:</strong> Impressoras Argox</div>
        </div>
        
        <div class="etiqueta-preview">
            <div class="big-e">E</div>
            <small>Etiqueta separadora entre SKUs</small>
        </div>
    </div>
    
    <form id="zplForm">
        <label for="zplCode"><strong>Cole seu código ZPL (etiqueta "E" automática):</strong></label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Sistema original com etiqueta 'E' separadora!"></textarea><br><br>
        <button type="submit">🎯 Gerar PDF com Etiqueta "E"</button>
    </form>
    
    <div id="result"></div>
    
    <script>
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            const button = e.target.querySelector('button');
            const result = document.getElementById('result');
            
            button.disabled = true;
            button.textContent = '⏳ Processando com etiqueta "E"...';
            result.innerHTML = '<div class="result processing">🔄 Detectando SKUs e inserindo etiquetas "E"...</div>';
            
            try {
                const response = await fetch('/generate-with-e', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'etiquetas_com_e.pdf';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    result.innerHTML = '<div class="result success">🎉 PDF gerado com etiquetas "E" separadoras! Download iniciado automaticamente.</div>';
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Erro desconhecido');
                }
                
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
            } finally {
                button.disabled = false;
                button.textContent = '🎯 Gerar PDF com Etiqueta "E"';
            }
        });
    </script>
</body>
</html>'''

def extract_first_code_from_block(zpl_block):
    """Extrai o primeiro código do bloco ZPL (para detectar mudança de SKU)"""
    # Procurar pelo primeiro ^FD...^FS (primeira linha de dados)
    match = re.search(r'\^FD([A-Za-z0-9\-_.]+)\^FS', zpl_block, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    return None

def create_etiqueta_e():
    """Cria etiqueta separadora com letra "E" grande"""
    return """^XA
^LH0,0
^FO400,50^A0N,120,120^FH^FDE^FS
^FO400,200^A0N,16,16^FH^FD--- SEPARADOR ---^FS
^XZ"""

@app.route('/generate-with-e', methods=['POST'])
def generate_with_e():
    """Processamento com etiqueta E separadora (como era antes)"""
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        
        print(f"🔄 Processamento com etiqueta E iniciado - {len(zpl_code)} caracteres")
        
        # Detectar blocos ZPL
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        
        if not zpl_blocks:
            # Se não encontrou blocos, assumir que é um bloco único
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            zpl_blocks = [zpl_code]
        
        print(f"📦 {len(zpl_blocks)} blocos detectados")
        
        # Inserir etiquetas "E" entre SKUs diferentes
        blocks_with_e = []
        last_sku = None
        e_count = 0
        
        for i, block in enumerate(zpl_blocks):
            current_sku = extract_first_code_from_block(block)
            
            print(f"📄 Bloco {i+1}: SKU = {current_sku}")
            
            # Se mudou de SKU, inserir etiqueta "E"
            if last_sku is not None and current_sku != last_sku and current_sku is not None:
                print(f"🔄 MUDANÇA DE SKU: {last_sku} → {current_sku} - Inserindo etiqueta E")
                blocks_with_e.append(create_etiqueta_e())
                e_count += 1
            
            blocks_with_e.append(block)
            if current_sku:
                last_sku = current_sku
        
        print(f"📄 {e_count} etiquetas 'E' inseridas")
        print(f"📦 Total de blocos: {len(blocks_with_e)} (originais + etiquetas E)")
        
        # Processar em lotes pequenos (como funcionava antes)
        pdf_merger = PdfMerger()
        batch_size = 10  # Lotes pequenos
        
        for i in range(0, len(blocks_with_e), batch_size):
            batch = blocks_with_e[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(blocks_with_e) + batch_size - 1) // batch_size
            
            print(f"⚡ Processando lote {batch_num}/{total_batches} ({len(batch)} blocos)")
            
            # Juntar blocos do lote
            batch_zpl = '\n'.join(batch)
            
            # Chamar API Labelary
            url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/pdf'
            }
            
            response = requests.post(url, data=batch_zpl, headers=headers, timeout=60)
            
            if response.status_code == 200:
                pdf_merger.append(io.BytesIO(response.content))
                print(f"✅ Lote {batch_num} processado com sucesso")
            else:
                print(f"❌ Erro no lote {batch_num}: {response.status_code}")
                return jsonify({'error': f'Erro na API Labelary: {response.status_code}'}), 500
        
        # Gerar PDF final
        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        pdf_merger.close()
        output_buffer.seek(0)
        
        # Salvar em arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(output_buffer.getvalue())
        temp_file.close()
        
        print(f"🎉 PDF final gerado: {len(zpl_blocks)} blocos originais + {e_count} etiquetas E")
        
        return send_file(temp_file.name, as_attachment=True, download_name='etiquetas_com_e.pdf')
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
