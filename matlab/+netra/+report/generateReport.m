function reportPath = generateReport(pipelineResult, imagePath, outputDir)
%GENERATEREPORT Assemble a NETRA-DR screening report (HTML) from a real pipeline result.
%
%   reportPath = netra.report.generateReport(pipelineResult, imagePath, outputDir)
%
% Entirely native MATLAB (no Python involved in report assembly). Distinguishes
% detected evidence (Phase 2) from model attention (Phase 4) and from the
% final screening decision (Phase 3) -- never merges them into one "proof"
% section. Every value written into the report comes directly from
% pipelineResult (produced by run_netradr_pipeline); nothing is invented for
% display purposes.

    if ~isfolder(outputDir)
        mkdir(outputDir);
    end
    [~, baseName] = fileparts(imagePath);
    timestamp = datestr(now, 'yyyy-mm-dd_HHMMSS'); %#ok<TNOW1,DATST>
    caseId = sprintf('%s_%s', baseName, timestamp);
    reportPath = fullfile(outputDir, [caseId '_report.html']);

    q = pipelineResult.quality;
    html = {};
    html{end+1} = '<!DOCTYPE html><html><head><meta charset="UTF-8">';
    html{end+1} = '<title>NETRA-DR Screening Report</title>';
    html{end+1} = ['<style>body{font-family:Segoe UI,Arial,sans-serif;background:#0b0f19;color:#e2e8f0;' ...
        'max-width:900px;margin:2rem auto;padding:0 1rem}h1{color:#38bdf8}h2{border-bottom:1px solid #263346;' ...
        'padding-bottom:.3rem;margin-top:2rem}table{border-collapse:collapse;width:100%}td,th{border:1px solid ' ...
        '#263346;padding:.4rem .6rem;text-align:left}.badge{padding:.2rem .6rem;border-radius:4px;font-weight:bold}' ...
        '.good{background:#14532d;color:#4ade80}.warn{background:#78350f;color:#fde047}.bad{background:#7f1d1d;' ...
        'color:#f87171}.disclaimer{border:1px dashed #3b4c63;padding:1rem;margin-top:2rem;font-size:.85rem;' ...
        'color:#94a3b8}</style></head><body>'];

    html{end+1} = '<h1>NETRA-DR Screening Report</h1>';
    html{end+1} = sprintf('<p><strong>Case ID:</strong> %s<br><strong>Timestamp:</strong> %s<br>', ...
        htmlEscape(caseId), datestr(now)); %#ok<DATST>
    html{end+1} = sprintf('<strong>Source image:</strong> %s</p>', htmlEscape(imagePath));

    html{end+1} = '<h2>Image Quality</h2>';
    qBadgeClass = qualityBadgeClass(q.quality_label);
    html{end+1} = sprintf('<p>Status: <span class="badge %s">%s</span> (score %.3f, model: %s)</p>', ...
        qBadgeClass, q.quality_label, q.quality_score, htmlEscape(q.model_name));
    html{end+1} = '<ul>';
    for i = 1:numel(q.reasons)
        html{end+1} = sprintf('<li>%s</li>', htmlEscape(q.reasons{i})); %#ok<AGROW>
    end
    html{end+1} = '</ul>';

    if isfield(pipelineResult, 'stopped_at_quality') && pipelineResult.stopped_at_quality
        html{end+1} = '<p><strong>Screening halted at the quality gate.</strong> Recapture is required; no downstream analysis was performed or fabricated.</p>';
        html{end+1} = disclaimerBlock();
        html{end+1} = '</body></html>';
        writeHtml(reportPath, html);
        return
    end

    html{end+1} = '<h2>Detected Retinal Evidence</h2>';
    html{end+1} = '<p><em>What the segmentation/detection modules found — separate from model attention below.</em></p>';
    html{end+1} = '<table><tr><th>Finding</th><th>Value</th></tr>';
    if isfield(pipelineResult, 'lesions')
        html{end+1} = sprintf('<tr><td>Hemorrhage present</td><td>%s</td></tr>', boolStr(pipelineResult.lesions.he_presence));
        html{end+1} = sprintf('<tr><td>Exudate area fraction</td><td>%.5f</td></tr>', pipelineResult.lesions.ex_area);
    else
        html{end+1} = '<tr><td>Lesion analysis</td><td>unavailable</td></tr>';
    end
    if isfield(pipelineResult, 'ma')
        html{end+1} = sprintf('<tr><td>Microaneurysm count</td><td>%d</td></tr>', pipelineResult.ma.ma_count);
    else
        html{end+1} = '<tr><td>Microaneurysm analysis</td><td>unavailable</td></tr>';
    end
    html{end+1} = sprintf('<tr><td>Neovascularization</td><td>%s</td></tr>', htmlEscape(pipelineResult.nv.status));
    html{end+1} = '</table>';

    html{end+1} = '<h2>DR Severity Grading</h2>';
    if isfield(pipelineResult, 'grading')
        g = pipelineResult.grading; cal = pipelineResult.calibration;
        icdrLabels = {'No DR', 'Mild NPDR', 'Moderate NPDR', 'Severe NPDR', 'Proliferative DR'};
        html{end+1} = sprintf('<p><strong>ICDR Grade %d — %s</strong> (model: %s v%s)</p>', ...
            g.severity_class, icdrLabels{g.severity_class + 1}, htmlEscape(g.model_name), htmlEscape(g.model_version));
        html{end+1} = '<table><tr><th>Grade</th><th>Raw prob.</th><th>Calibrated prob.</th></tr>';
        for i = 1:5
            html{end+1} = sprintf('<tr><td>%d</td><td>%.4f</td><td>%.4f</td></tr>', ...
                i-1, g.probabilities(i), cal.calibrated_probabilities(i)); %#ok<AGROW>
        end
        html{end+1} = '</table>';
        html{end+1} = sprintf('<p>Calibration: %s (temperature=%.2f)</p>', ...
            ternaryStr(cal.fitted, 'fitted', 'NOT fitted (raw probabilities)'), cal.temperature);
    else
        html{end+1} = '<p>Grading unavailable: model artifact not found.</p>';
    end

    html{end+1} = '<h2>Model Attention</h2>';
    html{end+1} = '<p><em>Model attention indicates image regions contributing to the model output; it is not a substitute for clinician interpretation.</em></p>';
    if isfield(pipelineResult, 'explainability')
        html{end+1} = sprintf('<p>Method: %s</p>', htmlEscape(pipelineResult.explainability.method_note));
    else
        html{end+1} = '<p>Model attention unavailable.</p>';
    end

    html{end+1} = '<h2>Referral Decision</h2>';
    if isfield(pipelineResult, 'decision')
        d = pipelineResult.decision;
        dBadge = ternaryStr(strcmp(d.referable_decision, 'REFER'), 'bad', 'good');
        html{end+1} = sprintf('<p>Fused decision: <span class="badge %s">%s</span> | Grade-alone decision: <span class="badge %s">%s</span></p>', ...
            dBadge, d.referable_decision, ternaryStr(strcmp(d.grade_alone_decision,'REFER'),'bad','good'), d.grade_alone_decision);
        html{end+1} = sprintf('<p>Decision layer: %s</p>', htmlEscape(d.fusion_status));
        html{end+1} = sprintf('<p>%s</p>', htmlEscape(d.reason));
    else
        html{end+1} = '<p>Referral decision unavailable: grading model not found.</p>';
    end

    html{end+1} = '<h2>Processing Time</h2>';
    html{end+1} = '<table><tr><th>Stage</th><th>Time (ms)</th></tr>';
    fns = fieldnames(pipelineResult.timing);
    for i = 1:numel(fns)
        html{end+1} = sprintf('<tr><td>%s</td><td>%.1f</td></tr>', htmlEscape(fns{i}), pipelineResult.timing.(fns{i}) * 1000); %#ok<AGROW>
    end
    html{end+1} = '</table>';

    html{end+1} = disclaimerBlock();
    html{end+1} = '</body></html>';
    writeHtml(reportPath, html);
end

function block = disclaimerBlock()
    block = ['<div class="disclaimer">NETRA-DR is a screening/triage research prototype (SIH26038). ' ...
        'It is NOT clinically validated, not a regulated medical device, and not diagnostically ' ...
        'definitive. All decisions require ophthalmologist confirmation. Detected evidence, model ' ...
        'attention, and the final screening decision are three distinct concepts and must not be ' ...
        'conflated.</div>'];
end

function s = htmlEscape(s)
    s = strrep(s, '&', '&amp;');
    s = strrep(s, '<', '&lt;');
    s = strrep(s, '>', '&gt;');
end

function s = boolStr(b)
    if b, s = 'Yes'; else, s = 'No'; end
end

function s = ternaryStr(cond, a, b)
    if cond, s = a; else, s = b; end
end

function c = qualityBadgeClass(label)
    switch upper(label)
        case 'GOOD', c = 'good';
        case 'BORDERLINE', c = 'warn';
        otherwise, c = 'bad';
    end
end

function writeHtml(path, htmlLines)
    fid = fopen(path, 'w');
    if fid < 0
        error('netra:report:writeFailed', 'Could not write report to: %s', path);
    end
    fprintf(fid, '%s\n', htmlLines{:});
    fclose(fid);
end
