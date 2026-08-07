// Teste simples para verificar se as funções serverless estão funcionando
exports.handler = async (event) => {
  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    },
    body: JSON.stringify({
      message: "Funcão serverless está funcionando!",
      path: event.path,
      method: event.httpMethod,
    }),
  };
};
