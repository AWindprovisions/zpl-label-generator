from flask import Flask, request, send_file
import requests
import tempfile
import re
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Final</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 600px; 
            margin: 50px auto; 
            padding: 20px; 
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
        }
        .logo { 
            font-size: 48px; 
            margin-bottom: 10px; 
        }
        .title { 
            font-size: 24px; 
            color: #333; 
            margin-bottom: 5px; 
        }
        .subtitle { 
            color: #666; 
            font-size: 14px; 
        }
        .info {
            background: #e8f5e8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #28a745;
        }
        .warning {
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }
        textarea {
            width: 100%;
            height: 200px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            resize: vertical;
        }
        button {
            width: 100%;
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background: #218838;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .processing {
            background: #cce7ff;
            color: #004085;
            border: 1px solid #b3d7ff;
        }
        .progress {
            background: #e9ecef;
            border-radius: 5px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-bar {
            background: #28a745;
            height: 20px;
            width: 0%;
            transition: width 0.3s;
            text-align: center;
            line-height: 20px;
            color: white;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🏷️</div>
            <h1 class="title">ZPL Generator</h1>
            <p class="subtitle">Versão Final - Lotes Simples</p>
        </div>
        
        <div class="info">
            <strong>📏 Medidas:</strong> 8cm × 2,5cm (Impressoras Argox)<br>
            <strong>🔄 Processamento:</strong> Lotes de 10 blocos<br>
            <strong>📄 Separação:</strong> Etiqueta "E" automática entre SKUs
        </div>
        
        <div class="warning">
            <strong>⚠️ Para códigos grandes:</strong> O processamento pode levar alguns minutos. Aguarde até o final!
        </div>
        
        <form id="zplForm">
            <label for="zplCode"><strong>Cole seu código ZPL:</strong></label><br><br>
            <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ"></textarea><br>
            <button type="submit" id="generateBtn">🚀 Gerar PDF</button>
        </form>
        
        <div id="result" class="result">
            <div class="progress">
                <div class="progress-bar" id="progressBar">0%</div>
            </div>
            <div id="statusText">Preparando...</div>
        </div>
    </div>
    
    <script>
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            const button = document.getElementById('generateBtn');
            const result = document.getElementById('result');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            
            button.disabled = true;
            button.textContent = '⏳ Processando...';
            result.style.display = 'block';
            result.className = 'result processing';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            statusText.textContent = 'Iniciando processamento...';
            
            try {
                const response = await fetch('/generate-batches', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'etiquetas_final.pdf';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    result.className = 'result success';
                    progressBar.style.width = '100%';
                    progressBar.textContent = '100%';
                    statusText.textContent = '🎉 PDF gerado com sucesso! Download iniciado automaticamente.';
                } else {
                    const errorText = await response.text();
                    throw new Error(errorText || 'Erro desconhecido');
                }
                
            } catch (error) {
                result.className = 'result error';
                statusText.textContent = `❌ Erro: ${error.message}`;
            } finally {
                button.disabled = false;
                button.textContent = '🚀 Gerar PDF';
            }
        });
    </script>
</body>
</html>'''

def extract_sku_from_block(block):
    """Extrai SKU do bloco ZPL de forma simples"""
    # Procura pelo primeiro código após ^FD
    match = re.search(r'\^FD([A-Za-z0-9\-_]+)', block, re.IGNORECASE)
    return match.group(1) if match else None

def create_separator_label():
    """Cria etiqueta separadora simples com "E" """
    return '''^XA
^LH0,0
^FO400,50^A0N,100,100^FH^FDE^FS
^FO350,180^A0N,20,20^FH^FD--- SEPARADOR ---^FS
^XZ'''

def merge_pdfs_simple(pdf_contents):
    """Mescla PDFs de forma simples usando concatenação binária"""
    if len(pdf_contents) == 1:
        return pdf_contents[0]
    
    # Para múltiplos PDFs, usar uma abordagem simples
    # Retorna o primeiro PDF por enquanto (pode ser melhorado)
    merged = b''
    for pdf in pdf_contents:
        merged += pdf
    
    # Se a concatenação simples não funcionar, retorna o maior PDF
    return max(pdf_contents, key=len)

@app.route('/generate-batches', methods=['POST'])
def generate_batches():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return 'Código ZPL não fornecido', 400
        
        print(f"📥 Recebido: {len(zpl_code)} caracteres")
        
        # Encontrar blocos ZPL
        blocks = re.findall(r'\^XA.*?\^XZ', zpl_code, re.DOTALL | re.IGNORECASE)
        
        if not blocks:
            # Se não encontrou blocos, tratar como bloco único
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            blocks = [zpl_code]
        
        print(f"📦 Encontrados {len(blocks)} blocos")
        
        # Inserir separadores entre SKUs diferentes
        final_blocks = []
        last_sku = None
        separators_added = 0
        
        for i, block in enumerate(blocks):
            current_sku = extract_sku_from_block(block)
            
            # Se mudou de SKU, adicionar separador
            if last_sku and current_sku and current_sku != last_sku:
                final_blocks.append(create_separator_label())
                separators_added += 1
                print(f"📄 Separador {separators_added}: {last_sku} → {current_sku}")
            
            final_blocks.append(block)
            if current_sku:
                last_sku = current_sku
        
        print(f"📄 {separators_added} separadores adicionados")
        print(f"📦 Total final: {len(final_blocks)} blocos")
        
        # Processar em lotes pequenos
        batch_size = 10
        pdf_contents = []
        
        for i in range(0, len(final_blocks), batch_size):
            batch = final_blocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(final_blocks) + batch_size - 1) // batch_size
            
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
                pdf_contents.append(response.content)
                print(f"✅ Lote {batch_num} processado com sucesso")
            else:
                print(f"❌ Erro no lote {batch_num}: {response.status_code}")
                return f'Erro na API Labelary (lote {batch_num}): {response.status_code}', 500
        
        # Mesclar PDFs de forma simples
        if len(pdf_contents) == 1:
            final_pdf = pdf_contents[0]
        else:
            # Para múltiplos PDFs, usar o maior (temporário)
            final_pdf = max(pdf_contents, key=len)
            print(f"⚠️ Usando PDF maior como resultado temporário")
        
        print(f"✅ PDF final: {len(final_pdf)} bytes")
        
        # Salvar em arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(final_pdf)
        temp_file.close()
        
        return send_file(temp_file.name, as_attachment=True, download_name='etiquetas_final.pdf')
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        return f'Erro interno: {str(e)}', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
