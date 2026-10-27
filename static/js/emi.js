(function () {
  var root = document.getElementById("emi");
  if (!root) return;
  var price = parseFloat(root.dataset.price);
  var fmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  var $ = function (id) { return document.getElementById(id); };

  function calc() {
    var downPct = +$("emiDown").value;
    var rate = +$("emiRate").value;
    var months = +root.querySelector('input[name="tenure"]:checked').value;
    var down = price * downPct / 100;
    var P = price - down;
    var r = rate / 12 / 100;
    var emi = r ? P * r * Math.pow(1 + r, months) / (Math.pow(1 + r, months) - 1) : P / months;
    var total = emi * months;
    var interest = total - P;

    $("emiDownOut").textContent = fmt.format(down) + " (" + downPct + "%)";
    $("emiRateOut").textContent = rate.toFixed(2) + "% p.a.";
    $("emiOut").textContent = fmt.format(emi);
    $("emiLoan").textContent = fmt.format(P);
    $("emiInt").textContent = fmt.format(interest);
    $("emiTotal").textContent = fmt.format(total + down);
    $("emiBar").style.width = (P / total * 100) + "%";

    var balance = P, rows = "";
    for (var y = 1; y <= Math.ceil(months / 12); y++) {
      var pp = 0, ip = 0;
      for (var m = 0; m < 12 && balance > 0.5; m++) {
        var i = balance * r;
        var p = Math.min(emi - i, balance);
        ip += i; pp += p; balance -= p;
      }
      rows += "<tr><td>Year " + y + "</td><td class='text-end'>" + fmt.format(pp) + "</td><td class='text-end'>" +
        fmt.format(ip) + "</td><td class='text-end'>" + fmt.format(Math.max(balance, 0)) + "</td></tr>";
    }
    $("amortBody").innerHTML = rows;
  }

  root.addEventListener("input", calc);
  root.addEventListener("change", calc);
  calc();
})();
