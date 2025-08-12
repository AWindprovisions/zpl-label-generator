from flask import Flask, request, render_template_string, jsonify, send_file
from flask_cors import CORS
import os, tempfile, requests, io, time, re, logging
from PyPDF2 import PdfMerger
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
app.secret_key = 'zpl-generator-manus-2025'
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024  # 50 GB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração inicial padrão (8cm × 2,5cm)
DEFAULT_WIDTH_CM = 8
DEFAULT_HEIGHT_CM = 2.5
DEFAULT_WIDTH_IN = round(DEFAULT_WIDTH_CM / 2.54, 2)
DEFAULT_HEIGHT_IN = round(DEFAULT_HEIGHT_CM / 2.54, 2)

def create_smart_batches(zpl_blocks, max_blocks=5, max_kb=500):
    """Cria lotes inteligentes limitados por blocos E tamanho em KB"""
    batches, current_batch, current_size = [], [], 0
    for block in zpl_blocks:
        block_size_kb = len(block) / 1024
        if (len(current_batch) >= max_blocks or current_size + block_size_kb > max_kb) and current_batch:
            batches.append(current_batch)
            current_batch, current_size = [], 0
        current_batch.append(block)
        current_size += block_size_kb
    if current_batch:
        batches.append(current_batch)
    return batches

def insert_blank_labels_between_skus(zpl_blocks):
    """Insere etiqueta em branco entre SKUs diferentes"""
    new_blocks = []
    last_sku = None
    blank_label = "^XA\n^FO0,0\n^GB800,250,0^FS\n^XZ"  # etiqueta em branco

    for block in zpl_blocks:
        match = re.search(r'\^FD([A-Za-z0-9\-_.]+)\^FS', block)
        current_sku = match.group(1) if match else None

        if last_sku is not None and current_sku != last_sku:
            new_blocks.append(blank_label)  # insere espaço

        new_blocks.append(block)
        last_sku = current_sku

    return new_blocks

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Arquivo muito grande. Limite: 50 GB'}), 413

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    temp_pdfs = []
    failed_blocks = []

    try:
        data = request.get_json()
        zpl_code = data.get('zpl_code', '').strip()

        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400

        # Regex tolerante para ^XA ... ^XZ
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        if not zpl_blocks:
            return jsonify({'error': 'Código ZPL inválido - nenhum bloco ^XA...^XZ encontrado'}), 400

        # Inserir etiquetas em branco entre SKUs diferentes
        zpl_blocks = insert_blank_labels_between_skus(zpl_blocks)

        total_blocks = len(zpl_blocks)
        total_size_kb = len(zpl_code) / 1024
        logger.info(f"🚀 PROCESSAMENTO: {total_blocks} blocos, {total_size_kb:.1f}KB")

        # Config adaptativa
        if total_blocks <= 10:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 10, 1000, 2, 30, 2
        elif total_blocks <= 100:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 5, 500, 3, 60, 3
        elif total_blocks <= 1000:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 3, 300, 5, 120, 4
        else:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 2, 200, 7, 300, 5

        WORKERS = min(WORKERS, os.cpu_count() * 2 if os.cpu_count() else 4)
        batches = create_smart_batches(zpl_blocks, MAX_BLOCKS, MAX_KB)
        logger.info(f"📦 {len(batches)} lotes criados")

        start_time = time.time()
        success_count = 0

        def process_batch(batch_index, batch):
            current_batch = batch[:]
            for attempt in range(MAX_RETRIES):
                pdf_data = generate_pdf_via_labelary(
                    '\n'.join(current_batch) + '\n',
                    TIMEOUT,
                    attempt + 1
                )
                if pdf_data:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    temp_file.write(pdf_data)
                    temp_file.close()
                    return {'success': True, 'pdf_path': temp_file.name, 'blocks': current_batch}
                if len(current_batch) > 1 and attempt < MAX_RETRIES - 1:
                    current_batch = current_batch[:len(current_batch)//2]
                    logger.warning(f"🔄 Fallback: lote {batch_index+1} reduzido para {len(current_batch)} blocos")
                time.sleep(2 ** attempt)
            return {'success': False, 'blocks': current_batch}

        # Processamento paralelo
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(process_batch, i, b): i for i, b in enumerate(batches)}
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    temp_pdfs.append(result['pdf_path'])
                    success_count += len(result['blocks'])
                else:
                    failed_blocks.extend(result['blocks'])

        # Reprocessar blocos falhos individualmente
        if failed_blocks:
            logger.warning(f"🔁 Reprocessando {len(failed_blocks)} blocos individuais")
            for i, block in enumerate(failed_blocks, 1):
                pdf_data = generate_pdf_via_labelary(block + '\n', TIMEOUT, 1)
                if pdf_data:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    temp_file.write(pdf_data)
                    temp_file.close()
                    temp_pdfs.append(temp_file.name)
                    success_count += 1

        if not temp_pdfs:
            return jsonify({'error': 'Nenhum bloco processado com sucesso'}), 500

        # Mesclar PDFs
        final_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        final_pdf.close()
        merger = PdfMerger()
        for pdf_path in temp_pdfs:
            merger.append(pdf_path)
        with open(final_pdf.name, 'wb') as f:
            merger.write(f)
        merger.close()

        # Limpeza
        for pdf_path in temp_pdfs:
            try: os.unlink(pdf_path)
            except: pass

        elapsed = time.time() - start_time
        logger.info(f"✅ CONCLUÍDO: {success_count}/{total_blocks} blocos, {elapsed:.1f}s")

        return send_file(final_pdf.name, as_attachment=True, download_name='etiquetas_zpl_otimizado.pdf')

    except Exception as e:
        logger.error(f"💥 Erro crítico: {e}")
        return jsonify({'error': str(e)}), 500

def generate_pdf_via_labelary(zpl_code, timeout=60, attempt=1):
    try:
        url = f"http://api.labelary.com/v1/printers/8dpmm/labels/{DEFAULT_WIDTH_IN}x{DEFAULT_HEIGHT_IN}/0/"
        headers = {'Content-Type': 'text/plain', 'Accept': 'application/pdf'}

        size_kb = len(zpl_code) / 1024
        if size_kb > 100:
            timeout = min(timeout * 2, 600)

        logger.info(f"📡 Labelary Tentativa {attempt} ({size_kb:.1f}KB, Timeout {timeout}s)")
        resp = requests.post(url, data=zpl_code.encode('utf-8'), headers=headers, timeout=timeout, stream=True)

        if resp.status_code == 200:
            buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    buf.write(chunk)
            return buf.getvalue()

        # Log detalhado do erro
        try:
            err_text = resp.content.decode(errors='ignore')
        except:
            err_text = "<erro ao decodificar>"
        logger.error(f"❌ Labelary HTTP {resp.status_code}: {err_text[:200]}")
        return None

    except requests.exceptions.Timeout:
        logger.warning(f"⏰ Timeout (Tentativa {attempt})")
        return None
    except Exception as e:
        logger.error(f"💥 Erro Labelary: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
