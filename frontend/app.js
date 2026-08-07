window.onerror = function(msg, src, line, col, err){

    console.error('Erro capturado:', msg);

    const loading =
      document.getElementById('loading');

    if(loading){
        loading.classList.add('hidden');
        loading.style.display = 'none';
    }

    return false;
}