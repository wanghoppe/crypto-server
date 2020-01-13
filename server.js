const http = require("http");
var amqp = require('amqplib/callback_api');
var conn_g;
var conn_g2;
var stored_lst;
// var second_object;



http
  .createServer((request, response) => {
    console.log("Requested url: " + request.url);

// _________________________________________________________________________________

    if (request.url.toLowerCase() === "/get_store") {
      response.writeHead(200, {
        // Connection: "keep-alive",
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
      });
      console.log('here')
      if ( stored_lst != "undefined") {
        response.write(stored_lst)
        response.write("\n\n")
      }else{
        response.write("body")
      }
      response.end()
      // request.end()

    }

// _________________________________________________________________________________

    if (request.url.toLowerCase() === "/get_second") {
      response.writeHead(200, {
        Connection: "keep-alive",
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
      });

      function res_func2 (data_msg) {
        let msg = 'data' + ':' + data_msg;
        // response.write('data:"-0.32718807"');
        response.write(msg);
        response.write("\n\n");
        // second_object = data_msg;
        // console.log(msg);
        // console.log(" [x] Received %s", msg.content.toString());
      };

      amqp.connect('amqp://hwa125:960923@ec2-3-19-67-238.us-east-2.compute.amazonaws.com', function(err, conn) {
        if (typeof conn_g2 != "undefined") {
           conn_g2.close()
           console.log('closed~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        }
        conn_g2 = conn;
        // console.log(conn_g);
        conn.createChannel(function(err, ch) {
          var q = 'predict-second';

          ch.assertQueue(q, {durable: false});
          console.log(" [*] Waiting for messages in %s. To exit press CTRL+C", q);
          ch.consume(q, function(msg) {

            let data_msg = msg.content.toString()

            res_func2(data_msg)

          }, {noAck: true});
        });
      });

      // console.log('here')
      // response.write(second_object)
      // response.write("\n\n")
      // response.end()
      // request.end()

    }

// _________________________________________________________________________________

    if (request.url.toLowerCase() === "/events") {
      response.writeHead(200, {
        // Connection: "keep-alive",
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
      });

      function res_func (data_msg) {
        let msg = 'data' + ':' + data_msg;
        // response.write('data:"-0.32718807"');
        response.write(msg);
        response.write("\n\n");
        stored_lst = data_msg;
        console.log(msg);
        // console.log(" [x] Received %s", msg.content.toString());
      };


      amqp.connect('amqp://hwa125:960923@ec2-3-19-67-238.us-east-2.compute.amazonaws.com', function(err, conn) {
        if (typeof conn_g != "undefined") {
           conn_g.close()
           console.log('conng, closed~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
           // console.log(conn)
        }
        conn_g = conn;
        // console.log(conn_g);
        conn.createChannel(function(err, ch) {
          var q = 'predict-24';
          // console.log(ch);
          ch.assertQueue(q, {durable: false});
          console.log(" [*] Waiting for messages in %s. To exit press CTRL+C", q);
          ch.consume(q, function(msg) {

            let data_msg = msg.content.toString()

            res_func(data_msg)

          }, {noAck: true});
        });
      });
      // console.log(conn_g);

    }
    // else {
    //   response.writeHead(404);
    //   response.end();
    // }
  })
  .listen(80, () => {
    console.log("Server running at http://127.0.0.1:80/");
  });
