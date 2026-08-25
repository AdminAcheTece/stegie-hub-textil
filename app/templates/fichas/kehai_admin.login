<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KEHAI — Painel de Pedidos</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/kehai_admin.css') }}?v={{ config.get('ASSET_VERSION','1') }}">
</head>
<body class="kehai-admin-page kehai-admin-login-page">

  <main class="kehai-admin-login">
    <section class="kehai-admin-login__card">
      <div class="kehai-admin-mark">KEHAI</div>
      <p class="kehai-admin-eyebrow">PÓS-VENDA</p>
      <h1>Painel de pedidos</h1>
      <p class="kehai-admin-muted">
        Área reservada para acompanhamento e preparação dos pedidos do livro KEHAI.
      </p>

      {% if error %}
        <div class="kehai-admin-alert kehai-admin-alert--error">{{ error }}</div>
      {% endif %}

      {% if not admin_configured %}
        <div class="kehai-admin-alert">
          Configure a variável <strong>KEHAI_ADMIN_PASSWORD</strong> no Render antes de acessar o painel.
        </div>
      {% endif %}

      <form method="post" class="kehai-admin-form">
        <label for="password">Senha administrativa</label>
        <input
          id="password"
          name="password"
          type="password"
          autocomplete="current-password"
          required
          autofocus
        >
        <button class="kehai-admin-btn kehai-admin-btn--primary" type="submit">
          Entrar
        </button>
      </form>
    </section>
  </main>

</body>
</html>
