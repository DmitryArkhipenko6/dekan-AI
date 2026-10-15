import { useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import SchoolOutlinedIcon from "@mui/icons-material/SchoolOutlined";

const documentTypes = [
  { value: "study_certificate", label: "Справка об обучении" },
  { value: "academic_leave", label: "Заявление на академический отпуск" },
  { value: "practice_certificate", label: "Справка о практике" },
];

const fieldLabels = {
  student_name: "ФИО студента",
  university: "Вуз",
  program: "Направление подготовки",
  study_mode: "Форма обучения",
  study_start: "Начало обучения",
  study_end: "Окончание обучения",
  certificate_number: "Номер документа",
  issue_date: "Дата выдачи",
  employee_signature: "Подпись сотрудника",
  university_stamp: "Печать вуза",
  group: "Учебная группа",
  course: "Курс",
  leave_reason: "Причина отпуска",
  leave_start: "Начало отпуска",
  leave_end: "Окончание отпуска",
  application_date: "Дата заявления",
  student_signature: "Подпись студента",
  organization: "Организация",
  practice_start: "Начало практики",
  practice_end: "Окончание практики",
  supervisor_name: "Руководитель практики",
  grade: "Оценка",
  supervisor_signature: "Подпись руководителя",
  organization_stamp: "Печать организации",
};

function sourceLabel(source) {
  if (source.startsWith("rule:")) return `Пункт ${source.slice(5)}`;
  if (source.startsWith("field:")) {
    return `Поле: ${fieldLabels[source.slice(6)] || source.slice(6)}`;
  }
  return source;
}

function App() {
  const [documentType, setDocumentType] = useState("study_certificate");
  const [question, setQuestion] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedType = useMemo(
    () => documentTypes.find((item) => item.value === documentType)?.label,
    [documentType],
  );

  async function submit(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!file) {
      setError("Сначала выберите файл документа.");
      return;
    }
    if (!question.trim()) {
      setError("Введите вопрос по документу.");
      return;
    }

    const body = new FormData();
    body.append("file", file);
    body.append("document_type", documentType);
    body.append("question", question.trim());

    setLoading(true);
    try {
      const response = await fetch("/api/check", {
        method: "POST",
        body,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Ошибка сервера (${response.status})`);
      }
      setResult(data);
    } catch (err) {
      setError(
        `${err.message}. Проверьте, что backend запущен и доступен по адресу /api/check.`,
      );
    } finally {
      setLoading(false);
    }
  }

  const answer = result?.answers?.[0];
  const isOk = result?.validation?.status === "document_ok";

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="static"
        elevation={0}
        sx={{ bgcolor: "primary.dark", borderBottom: "4px solid", borderColor: "secondary.main" }}
      >
        <Toolbar sx={{ minHeight: 70, gap: 1.5 }}>
          <SchoolOutlinedIcon sx={{ fontSize: 32, color: "#f5b45b" }} />
          <Box>
            <Typography variant="h6" fontWeight={700} lineHeight={1.15}>
              Онлайн-деканат
            </Typography>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,.72)" }}>
              Предварительная проверка студенческих документов
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: { xs: 4, md: 7 } }}>
        <Stack spacing={1} sx={{ mb: 4 }}>
          <Chip
            icon={<FactCheckOutlinedIcon />}
            label="Цифровой помощник студента"
            color="primary"
            variant="outlined"
            sx={{ width: "fit-content", bgcolor: "white" }}
          />
          <Typography variant="h4" sx={{ mt: 1 }}>
            Проверьте документ и задайте вопрос
          </Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 700 }}>
            Загрузите фото или скан. Сервис распознает текст и подготовит
            предварительный ответ со ссылками на поля документа и пункты Положения.
          </Typography>
        </Stack>

        <Card>
          <CardContent sx={{ p: { xs: 2.5, sm: 4 } }}>
            <Box component="form" onSubmit={submit}>
              <Stack spacing={2.5}>
                <FormControl fullWidth>
                  <InputLabel id="doc-type-label">Тип документа</InputLabel>
                  <Select
                    labelId="doc-type-label"
                    value={documentType}
                    label="Тип документа"
                    onChange={(event) => setDocumentType(event.target.value)}
                  >
                    {documentTypes.map((type) => (
                      <MenuItem key={type.value} value={type.value}>
                        {type.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Box>
                  <Button
                    component="label"
                    fullWidth
                    variant="outlined"
                    startIcon={<CloudUploadOutlinedIcon />}
                    sx={{
                      minHeight: 64,
                      justifyContent: "flex-start",
                      borderStyle: "dashed",
                      bgcolor: "#fbfdfc",
                    }}
                  >
                    {file ? file.name : "Выбрать файл JPG, PNG или PDF"}
                    <input
                      hidden
                      type="file"
                      accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                      onChange={(event) => setFile(event.target.files?.[0] || null)}
                    />
                  </Button>
                  {file && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                      {selectedType} · {(file.size / 1024 / 1024).toFixed(2)} МБ
                    </Typography>
                  )}
                </Box>

                <TextField
                  fullWidth
                  label="Ваш вопрос"
                  placeholder="Например: Какова дата выдачи?"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  multiline
                  minRows={2}
                  inputProps={{ maxLength: 500 }}
                />

                {error && <Alert severity="error">{error}</Alert>}

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading}
                  startIcon={
                    loading ? <CircularProgress size={18} color="inherit" /> : <DescriptionOutlinedIcon />
                  }
                  sx={{ alignSelf: { xs: "stretch", sm: "flex-start" } }}
                >
                  {loading ? "Проверяем документ…" : "Проверить и ответить"}
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>

        {result && (
          <Stack spacing={2.5} sx={{ mt: 3 }}>
            <Card>
              <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", sm: "center" }}
                  spacing={1.5}
                  sx={{ mb: 2 }}
                >
                  <Typography variant="h5">Результат проверки</Typography>
                  <Chip
                    label={isOk ? "Все обязательные сведения найдены" : "Есть незаполненные поля"}
                    color={isOk ? "success" : "warning"}
                    variant="outlined"
                  />
                </Stack>

                {answer && (
                  <Alert severity={answer.answerable ? (isOk ? "success" : "info") : "warning"}>
                    <Typography>{answer.answer}</Typography>
                    {!!answer.sources?.length && (
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                        {answer.sources.map((source) => (
                          <Chip key={source} size="small" label={sourceLabel(source)} />
                        ))}
                      </Stack>
                    )}
                  </Alert>
                )}

                {result.validation?.missing_fields?.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography fontWeight={700} gutterBottom>
                      Не найдены обязательные поля
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {result.validation.missing_fields.map((key) => (
                        <Chip
                          key={key}
                          label={fieldLabels[key] || key}
                          color="warning"
                          variant="outlined"
                        />
                      ))}
                    </Stack>
                  </Box>
                )}

                <Divider sx={{ my: 2.5 }} />
                <Typography fontWeight={700} gutterBottom>
                  Распознанные поля
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                    gap: 1.25,
                  }}
                >
                  {Object.entries(result.fields || {}).map(([key, value]) => (
                    <Box
                      key={key}
                      sx={{ p: 1.5, bgcolor: "#f5f8f7", borderRadius: 2, minWidth: 0 }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {fieldLabels[key] || key}
                      </Typography>
                      <Typography sx={{ overflowWrap: "anywhere" }}>
                        {value || "не найдено"}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>

            {result.notice && (
              <Alert severity="info">{result.notice}</Alert>
            )}
          </Stack>
        )}

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mt: 4, textAlign: "center" }}
        >
          Результат является предварительной проверкой. Окончательное решение принимает сотрудник деканата.
        </Typography>
      </Container>
    </Box>
  );
}

export default App;
